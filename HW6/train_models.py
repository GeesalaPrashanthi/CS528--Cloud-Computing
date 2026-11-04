"""Deterministic held-out evaluation; select income model using training-only validation."""
import argparse
import json
import os
from pathlib import Path
import pandas as pd
import pymysql
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, OrdinalEncoder
from sklearn.tree import DecisionTreeClassifier


def load_data(source_view="request_details"):
    from db import connect
    conn = connect()
    try:
        with conn.cursor() as cur:
            # Observations remain distinct from any inferred canonical IP-country map.
            cur.execute(f'''SELECT request_id, client_ip, country, age, gender, income,
                is_banned, http_status, time_of_day, requested_file
                FROM {source_view} ORDER BY request_id''')
            return pd.DataFrame(cur.fetchall(), columns=[x[0] for x in cur.description])
    finally:
        conn.close()


def pipeline(features, estimator, ordinal=False):
    encoder = (OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1)
               if ordinal else OneHotEncoder(handle_unknown='ignore'))
    return Pipeline([('encode', ColumnTransformer([('categories', encoder, features)])),
                     ('model', estimator)])


def run(df, output):
    output.mkdir(parents=True, exist_ok=True)
    metrics = {'seed':42, 'split':'80% training, 20% final test; 25% of training for income validation',
               'loaded_rows':len(df)}
    country = df.dropna(subset=['client_ip', 'country']).copy()
    train, test = train_test_split(country, test_size=.2, random_state=42)
    # Choose exact address vs /24 network using only a validation split of training rows.
    fitting, validation = train_test_split(train, test_size=.2, random_state=43)
    def key(frame, strategy):
        return frame.client_ip if strategy == 'exact_ip' else frame.client_ip.str.rsplit('.', n=1).str[0]
    def fit_map(frame, strategy):
        pairs = pd.DataFrame({'key':key(frame, strategy), 'label':frame.country})
        counts = pairs.groupby(['key','label'], sort=False).size().reset_index(name='count')
        winners = counts.sort_values('count', ascending=False, kind='stable').drop_duplicates('key')
        return winners.set_index('key').label
    def predict(frame, learned, default, strategy):
        return key(frame, strategy).map(learned).fillna(default)
    scores = {}
    for strategy in ['exact_ip', 'network_prefix_24']:
        learned = fit_map(fitting, strategy)
        scores[strategy] = float(accuracy_score(validation.country,
            predict(validation, learned, fitting.country.mode().iloc[0], strategy)))
    selected_country = max(scores, key=scores.get)
    mapping = fit_map(train, selected_country)
    prediction = predict(test, mapping, train.country.mode().iloc[0], selected_country)
    metrics['country'] = {'accuracy':float(accuracy_score(test.country, prediction)),
        'test_rows':len(test), 'training_rows':len(train), 'model':selected_country,
        'validation_scores':scores,
        'unseen_test_keys':int((~key(test, selected_country).isin(mapping.index)).sum()),
        'conflicting_ips':int((country.groupby('client_ip').country.nunique()>1).sum()),
        'empirical_full_data_ceiling':float(country.groupby(['client_ip','country']).size()
            .groupby(level=0).max().sum()/len(country))}
    pd.DataFrame({'request_id':test.request_id, 'actual':test.country,
                  'predicted':prediction}).to_csv(output/'country_predictions.csv', index=False)

    income = df.dropna(subset=['income','age','gender']).copy()
    base = ['age','gender']
    extra = ['age','gender','country','time_of_day','http_status','is_banned']
    for col in extra:
        income[col] = income[col].fillna('__MISSING__').astype(str)
    development, final_test = train_test_split(income, test_size=.2, random_state=42,
                                              stratify=income.income)
    fitting, validation = train_test_split(development, test_size=.25, random_state=43,
                                           stratify=development.income)
    candidates = {
      'demographic_tree':pipeline(base, DecisionTreeClassifier(max_depth=8, random_state=42)),
      'demographic_forest':pipeline(base, RandomForestClassifier(n_estimators=100,
                                      max_depth=8, random_state=42, n_jobs=2)),
      'context_tree':pipeline(extra, DecisionTreeClassifier(max_depth=10,
                                     min_samples_leaf=100, random_state=42)),
      'context_boosting':pipeline(extra, HistGradientBoostingClassifier(max_iter=60,
                                      max_leaf_nodes=15, l2_regularization=10,
                                      random_state=42), ordinal=True),
    }
    scores = {}
    for name, model in candidates.items():
        model.fit(fitting, fitting.income)
        scores[name] = float(accuracy_score(validation.income, model.predict(validation)))
        print(f'Validation {name}: {scores[name]:.4%}', flush=True)
    selected = max(scores, key=scores.get)
    model = candidates[selected]
    model.fit(development, development.income)
    prediction = model.predict(final_test)
    metrics['income'] = {'model':selected, 'validation_scores':scores,
        'accuracy':float(accuracy_score(final_test.income, prediction)),
        'test_rows':len(final_test), 'training_rows':len(development),
        'features':base if selected.startswith('demographic') else extra,
        'excluded_features':['request_id','request_time','income','requested_file','client_ip']}
    pd.DataFrame({'request_id':final_test.request_id,'actual':final_test.income,
                  'predicted':prediction}).to_csv(output/'income_predictions.csv', index=False)
    (output/'metrics.json').write_text(json.dumps(metrics, indent=2)+'\n')
    print(json.dumps(metrics, indent=2), flush=True)
    return metrics


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-view', choices=['request_details'], default='request_details')
    parser.add_argument('--input-csv', type=Path, help='Optional local snapshot; never commit it')
    parser.add_argument('--output-dir', type=Path, default=Path('outputs'))
    parser.add_argument('--bucket', default='cs528-hw2-pgeesala')
    parser.add_argument('--prefix', default='hw6')
    parser.add_argument('--upload', action='store_true')
    args = parser.parse_args()
    df = pd.read_csv(args.input_csv) if args.input_csv else load_data(args.source_view)
    run(df, args.output_dir)
    if args.upload:
        from google.cloud import storage
        bucket = storage.Client().bucket(args.bucket)
        for name in ['country_predictions.csv','income_predictions.csv','metrics.json']:
            dest = f'{args.prefix.strip("/")}/{name}'
            bucket.blob(dest).upload_from_filename(str(args.output_dir/name))
            print(f'Uploaded gs://{args.bucket}/{dest}', flush=True)

if __name__ == '__main__':
    main()
