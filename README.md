# Ur III Transaction Parser

Detect and retrieve transactions in the Ur III corpus.

Components
==

- CFG parser for semantic parsing
	
	`jaworski.cfg` CFG grammar, slightly enriched extraction patterns as defined by Jaworski (2008)

	`jaworski.py` for parsing plain text, one line at a time. Optimised for speed, not accuracy.

	`jaworski4conll.py` for parsing with pre-annotations (CDLI-CoNLL: tokenization, morphology, CoNLL-U/CDLI-CoNLL: dependency syntax).
	Can process multi-line tokens. Implements a preference ranking over possible start symbols by means of iterated parses with different start symbols. Relatively slow.

	Note that current development focuses on `jaworski4conll.py`.
	
- Experimental conversion to UD dependency labels. This also provides routines to connect all partial analyses into a 
  single result graph. Note that these "repair operations" are rather slow.

	`jaworski2deps.sh`

- Workflow demonstration on sample data (CoNLL only)

	`demo.sh`

Note: For high-precision parsing, we recommend jaworski4conll.py. 
The primary application of this parser is to mine gold data to train annotators on. It is not optimized for speed,
but aims to maximize recall while maintaining a maximum level of precision. Therefore, the parser is iteratively applied: 
To produce partial parses, it re-iterates over the CFG grammar using different start symbols. For production mode, use 
jaworski.py.

Acknowledgements
==

Author : Christian Chiarcos, Goethe Unviersität Frankfurt

Developed by the MTAAC project (2017-2020) for the CDLI.
Partially supported by the research group "Linked Open Dictionaries" (LiODi, funded 2015-2020 as an eHumanities research group by the German Federal 
Ministry of Education and Research, BMBF)

The CFG parser replicates the semantic parser described by Jaworski 2008 (https://dl.acm.org/doi/10.5555/1599081.1599128), albeit with a different technology.
