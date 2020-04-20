
TODO: support searching submissions too

TODO: grabbing comments from large posts is very slow right now; see if that can be fixed.

TODO: indices should support incremental updating.  `refresh.py` is a step in this direction, but all the new comments need to be written somewhere so `build_comment_db.py` and `build_index.py` can read from it and only touch newly added comments.

# What is this?

This is code does a few things

1. Uses reddit.com's API to fetch/save comments

2. Build an index of those comments

3. Serve a webpage that lets you search those comments

# Overview

On my computer I have a directory called 'comments' (not uploaded to Github as it is very large). `python refresh.py` fetches all comments from submissions that were created in the last 2 weeks and adds them to this directory as JSONs (e.g. "comments/2017/5lfpf6.json").

Then `python build_comment_db.py` takes these JSONs and constructs a SQL database.  We try to keep the JSONs in comments/... relatively unprocessed (though there is some mild inconsistencies based on how refresh.py has changed over time.), so this SQL table gives us the chance to modify the JSONs while preserving the original JSONs.  All other scripts should only refer to this SQL table (this restriction is for the sanity of development).

The `python build_index.py --score=score --outdir=index` builds an index so we can retrieve comments quickly.  We construct an index for every type of ordering we support (e.g. `--score=new`, etc.), so our index directory looks like:

```
index/
  score/
    ...
  new/
    ...
  old/
    ...
  depth/
    ...
```

With each subdirectory containing thousands of '.list' files.  A '.list' file looks something like

```
...
hzzzzyy e9876mi
hzzzzyy e98gh2q
hzzzzyy e998ztf
hzzzzyy e9a5wao
hzzzzyy e9bqpdf
...
```

Every line contains a base-36 encoded integer and a (reddit) submission id.  The score corresponds to whatever we're sorting the file by (e.g. the comment's score, date-of-creating, etc.)  The entire file is sorted alphabetically (which is equivalent to sorting numerically by score).

Each list corresponds to some token (e.g. there is a list which contains every comment with the word "carrots").  When a user types "apple carrots", we find the (two) lists that correspond to each word and perform a set intersection in O(n) time (since the lists are sorted).

In the future we hope to support arbitrary union/intersection, but right now only intersection is supported (e.g. you cannot yet query for comments that contain "apple OR carrots").

In addition to having tokens (and corresponding '.list' files) for each word in a comment, we also have tokens for authors, depths, scores, years, etc.  While most of these are (behind the scenes) functionally identical to word tokens, there are a handful that require special care (see 'Interval Search' below).

As a practical matter, we hash tokens to an integer between zero and 8,192 (at the time of writing).  Without this we'd make tens of thousands of files that contain less than 10 comments (for example only ten comments have the word "hippo" in them).

The hashing can make our retrieved results incorrect (due to hash collisions), so after the initial retrieval we fetch the candidate and perform a final pass to make sure it is correct.  Unfortunately this final pass requires fetching the JSON from the SQL table which is (comparatively) slow, so false positives (from hash collisions) can be costly.

One final note: retrieval is written entirely using iterators, so that we can return as soon as we have the desired number of results (without having to process the entire '.list' file).

# Interval Search

(None of this is implemented yet).

The trickiest part of this token-list retrieval is supporting the ability to filter based on numeric intervals.  This is relevant for searching by time, score, and depth.

Depth is the easiest, as the range is very limited (in practice).  Simply having a token for each depth and unioning them works fine (on my laptop unioning is extremely fast for up to \~200 lists).  The only caveat is that we clip depths to 20 during retrieval, since the number of comments above depth=19 is vanishingly small.

Score and time, on the other hand, have wide enough ranges that this approach would require unioning dozens or even hundreds of lists.  Another approach is clearly needed.

Instead we have sets of tokens for different sized intervals.  This is easiest for time, where we have a token for each 1-day, 4-day, 16-day, 64-day, and 256-day interval.  Answering a user's arbitrary interval request then boils down to figuring out the fewest intervals we can use to (conserviatively) approximate it.  Example

```
Query        2  3  4  5  6  7  8  9  a
time0 [0][1][2][3][4][5][6][7][8][9][a][b][c][d][e][f] ...
time1 [0  1  2  3][4  5  6  7][8  9  a  b][c  d  e  f] ...
time2 [0  1  2  3  4  5  6  7  8  9  a  b  c  d  e  f] ...
```

Rather than performing 8 unions, we can perform 4: (\[23\] + \[4567\] + \[8\] + \[9\] + \[a\]).  Importantly, this grows only logarithmically with the length of the interval (rather than linearly).

TODO: run some benchmarks to find the actual best branching factor

TODO: set-difference can be performed efficiently.  Does using set difference here help speed these queries up?

## Score Distribution

Fast search for comment score is a little trickier.  The above approach is optimal for intervals that are uniform, but comment scores have long tails.

To be more specific, comments over a score of 1 follow an exponential distribution almost perfectly (see score_distribution.png), with

```
p(score = x) = exp(-0.10596903 * x - 2.37438391)
```

For scores less -1 the fit is decent as well:

```
p(score = x) = exp(0.22739776 * x - 5.81805568)
```

An efficient interval-ing method would have fewer intervals at the sparser parts of the curve -- for instance, having a single token for comments with a score of 184 gains you nothing (except needing more, nearly-empty files), since only 1 in 27 million comments have exactly that score.  A single token can cover the interval from 200 to infinity completely adaquately.

Ideally, we'd have every token at a given level cover the same proportion of the comments (e.g. 256 low-level tokens covering 0.4% of comments each, 64 mid-level tokens covering 1.6% each, and 16 high-level tokens covering 6.25% of comments each, and 4 highest-level tokens covering 25% each).

In real life this distribution is discrete and we have to approximate.  We have a total of 44 low-level tokens, with every score from -3 to 30 (inclusive) having its own token.  The remaining tokens are:

```
(-inf, 5] [-6, -4] [-3] [-2] ... [29] [30] [31,32] [33,34] [35,36] [37,38] [39,42] [43,47] [48,56] [56,inf)

```

These tokens were chosen so that each interval has around 0.4% of the comments.  On first blush it might seem strange that we only ended up with 44 tokens, rather than our (desired) 256.  This is a result of 95.9% of the distribution lying on the interval [-3, 30].  That we only have 44 tokens is not a reflection of a poor job optimizing these intervals, but rather due to the discrete nature of the scores.  With some thought you can hopefully convince yourself that this won't be a problem for performance.

All levels live in score_intervals.txt.

# Efficient Intersection/Union Queries

TODO: we hope to optimize union/intersection queries...

