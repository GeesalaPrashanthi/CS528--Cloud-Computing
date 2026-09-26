from google.cloud import storage
from collections import deque
import re
import time

BUCKET_NAME='cs528-hw2-pgeesala'
PREFIX='pages/'

def read_graph():
    client=storage.Client.create_anonymous_client()
    blobs=client.list_blobs(BUCKET_NAME,prefix=PREFIX)
    graph={}
    count=0

    for blob in blobs:
        if not blob.name.endswith('.html'):
            continue

        file_name=blob.name.split('/')[-1]
        page=int(file_name.replace('.html',''))
        text=blob.download_as_text()
        links=re.findall(r'HREF="(\d+)\.html"',text)
        graph[page]=[int(link) for link in links]

        count+=1
        if count%500==0:
            print('Files read:',count)

    return graph

def build_incoming(graph):
    incoming={}

    for page in graph:
        incoming[page]=[]

    for page in graph:
        for link in graph[page]:
            if link in incoming:
                incoming[link].append(page)

    return incoming

def median(values):
    values=sorted(values)
    n=len(values)

    if n%2==1:
        return values[n//2]

    return (values[n//2-1]+values[n//2])/2

def quintiles(values):
    values=sorted(values)
    n=len(values)

    return [
        values[int((n-1)*0.20)],
        values[int((n-1)*0.40)],
        values[int((n-1)*0.60)],
        values[int((n-1)*0.80)]
    ]

def print_stats(name,values):
    print(name)
    print('Average:',sum(values)/len(values))
    print('Median:',median(values))
    print('Maximum:',max(values))
    print('Minimum:',min(values))
    print('Quintiles:',quintiles(values))

def pagerank(graph,incoming):
    n=len(graph)
    rank={}

    for page in graph:
        rank[page]=1/n

    iteration=0

    while True:
        new_rank={}

        for page in graph:
            value=0.15/n

            for source in incoming[page]:
                if len(graph[source])>0:
                    value+=0.85*(rank[source]/len(graph[source]))

            new_rank[page]=value

        old_sum=sum(rank.values())
        new_sum=sum(new_rank.values())

        percent_change=abs(new_sum-old_sum)/old_sum*100

        rank=new_rank
        iteration+=1

        if percent_change<=0.5:
            break

    print('PageRank iterations:',iteration)
    return rank

def shortest_paths(graph,start):
    distances={start:0}
    queue=deque([start])

    while queue:
        current=queue.popleft()

        for neighbor in graph[current]:
            if neighbor not in distances:
                distances[neighbor]=distances[current]+1
                queue.append(neighbor)

    return distances

def best_closeness(graph):
    best_page=None
    best_score=-1
    n=len(graph)

    for page in graph:
        distances=shortest_paths(graph,page)
        reachable=len(distances)-1

        if reachable==0:
            score=0
        else:
            distance_sum=sum(distances.values())
            score=(reachable/distance_sum)*(reachable/(n-1))

        if score>best_score:
            best_score=score
            best_page=page

    return best_page,best_score

def test_pagerank():
    graph={
        0:[1],
        1:[2],
        2:[0]
    }

    incoming=build_incoming(graph)
    ranks=pagerank(graph,incoming)

    assert abs(ranks[0]-ranks[1])<0.001
    assert abs(ranks[1]-ranks[2])<0.001
    print('PageRank test passed')

def test_closeness():
    graph={
        0:[1],
        1:[0,2,3],
        2:[1],
        3:[1]
    }

    page,score=best_closeness(graph)

    assert page==1
    print('Closeness centrality test passed')

# run the functions
start=time.perf_counter()

print('Running tests...')
test_pagerank()
test_closeness()

print()
print('Reading files from Google Cloud Storage...')
graph=read_graph()
print('Pages loaded:',len(graph))

incoming=build_incoming(graph)

outgoing_counts=[]
incoming_counts=[]

for page in graph:
    outgoing_counts.append(len(graph[page]))
    incoming_counts.append(len(incoming[page]))

print_stats('\nOutgoing Links',outgoing_counts)

print_stats('\nIncoming Links',incoming_counts)

print('\nCalculating PageRank...')
ranks=pagerank(graph,incoming)

top_pages=sorted(ranks.items(),key=lambda x:x[1],reverse=True)[:5]

print('Top 5 pages by PageRank:')
for page,score in top_pages:
    print(page,score)

print('\nCalculating closeness centrality...')
page,score=best_closeness(graph)

print('Page with best closeness centrality:',page)
print('Closeness centrality score:',score)

end=time.perf_counter()

print('\nTotal runtime:',end-start,'seconds')