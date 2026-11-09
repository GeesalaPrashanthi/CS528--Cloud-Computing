"""CS528 HW7: Top incoming/outgoing links and word trigrams using Beam."""
import argparse
import html
import re
from html.parser import HTMLParser

import apache_beam as beam
from apache_beam.io import fileio
from apache_beam.options.pipeline_options import PipelineOptions

LINK_RE = re.compile(r'\bHREF\s*=\s*["\'](\d+)\.html["\']', re.IGNORECASE)
WORD_RE = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def read_page(readable):
    path = readable.metadata.path
    name = path.rsplit('/', 1)[-1]
    with readable.open() as f:
        contents = f.read().decode('utf-8')
    return name, contents


def outgoing(page):
    name, body = page
    return (name, len(LINK_RE.findall(body)))


def incoming_edges(page):
    _, body = page
    for target in LINK_RE.findall(body):
        yield (target + '.html', 1)


def trigrams(page):
    _, body = page
    parser = TextExtractor()
    parser.feed(body)
    words = WORD_RE.findall(html.unescape(' '.join(parser.parts)).lower())
    for i in range(len(words) - 2):
        yield (' '.join(words[i:i + 3]), 1)


def format_top(items):
    for rank, (key, count) in enumerate(items, start=1):
        yield f'{rank}. {key}: {count}'


def run(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', default='gs://cs528-hw2-pgeesala/pages/*.html')
    parser.add_argument('--output', required=True)
    args, beam_args = parser.parse_known_args(argv)
    options = PipelineOptions(beam_args, save_main_session=True)

    with beam.Pipeline(options=options) as p:
        pages = (
            p | 'Find HTML pages' >> fileio.MatchFiles(args.input)
              | 'Read HTML pages' >> fileio.ReadMatches()
              | 'Decode HTML pages' >> beam.Map(read_page)
        )

        # Outgoing links: count HREF entries per source page.
        out_counts = pages | 'Outgoing counts' >> beam.Map(outgoing)
        (
            out_counts
            | 'Top outgoing' >> beam.combiners.Top.Of(5, key=lambda kv: (kv[1], kv[0]))
            | 'Format outgoing' >> beam.FlatMap(format_top)
            | 'Write outgoing' >> beam.io.WriteToText(args.output + '/top_outgoing', shard_name_template='')
        )

        # Include zero incoming counts, if any, by seeding every page with zero.
        initial_counts = pages | 'Initialize incoming' >> beam.Map(lambda page: (page[0], 0))
        link_counts = pages | 'Extract incoming edges' >> beam.FlatMap(incoming_edges)
        inc_counts = (
            (initial_counts, link_counts)
            | 'Merge incoming streams' >> beam.Flatten()
            | 'Sum incoming' >> beam.CombinePerKey(sum)
        )
        (
            inc_counts
            | 'Top incoming' >> beam.combiners.Top.Of(5, key=lambda kv: (kv[1], kv[0]))
            | 'Format incoming' >> beam.FlatMap(format_top)
            | 'Write incoming' >> beam.io.WriteToText(args.output + '/top_incoming', shard_name_template='')
        )

        tri_counts = (
            pages | 'Extract word trigrams' >> beam.FlatMap(trigrams)
                  | 'Count trigrams' >> beam.CombinePerKey(sum)
        )
        (
            tri_counts
            | 'Top trigrams' >> beam.combiners.Top.Of(5, key=lambda kv: (kv[1], kv[0]))
            | 'Format trigrams' >> beam.FlatMap(format_top)
            | 'Write trigrams' >> beam.io.WriteToText(args.output + '/top_trigrams', shard_name_template='')
        )


if __name__ == '__main__':
    run()
