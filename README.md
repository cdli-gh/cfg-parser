
# Ur III Transaction Parser

Detect and retrieve transactions in the Ur III corpus.
- Workflow demonstration on sample data (for all supported input formats)

		`demo.sh`

For practical annotation, we recommend the document-level parser, but as it depends on specific pre-annotation for commodities (`COM`), you might want to look in the older transaction-level parsers. 



Document-level parser 
==

- `parse_comm.py`

	- semantic parser for transctions in the MTAAC Ur III corpus
	- requires pre-annotations for POS and COMM(odities) in accordance with https://github.com/cdli-gh/mtaac_cdli_ur3_corpus/tree/master/ur3_corpus_data/annotated/comm_conll
	- 
	  column structure of input format:
	  
			WORD SEGM POS MORPH CODE CHK ... 
		
		with
		
			WORD transcription 
			SEGM morpheme segmentation (currently not used)
			POS part-of-speech tag, MTAAC schema
			MORPH morphosyntactic analysis, MTAAC schema (currently not used)
			CODE (ignored) 
			CHK IOB-coded chunk structure, expected labels B-COUNT, I-COUNT, B-COM, I-COM, B-MOD, I-MOD 

		If additional (following columns) are provided, these will be ignored and excluded from the output.
			
	- two-level parsing for full documents
		- heuristic splitting into transaction segments before `COM` and `szunigin`
		- `parse_comm.cfg`: CFG parsing for every segment, inspired by Jaworski 2008, but using a different technology
		- `parse_doc.cfg`: fast left-to-right parsing over the resulting partial parses for the full document
		  As we use a regular grammar, this is strictly right-branching. Attachment needs to be revised.
		- post modifications, i.e., adjustments to attachment, removal of placeholder symbols

	- run with
	
			$> python3 parse_comm.py your-file.conll > annotated.conll
		
			usage: parse_comm.py [-h] [--debug] [--conll] [--ptb] [--rawDoc]
                     [FILE.conll [FILE.conll ...]]

			positional arguments:
				  FILE.conll  CoNLL/TSV files, without arguments, use input/comm/P106438.conll

			optional arguments:
			  --debug     write base grammar and original text, entails --ptb
			  --conll     if --debug, --ptb, or --rawDoc: return CoNLL output in addition
						  to PTB output
			  --ptb       return a PTB parse instead of the default (CoNLL) output. This
						  is informative only and lossy, to enable CoNLL output in
						  addition to --ptb, use --conll
			  --rawDoc    for debugging: disable post modifications
						  return the raw document parse as produced by
						  parse_doc.cfg, entails --ptb

	Output in a CoNLL/TSV format (default or flag `--conll`) or PTB-style bracket notation (`--ptb`). The latter is human-readable, but less compact and omits essential information. It is recommended for debugging, but not for subsequent processing.
	
PTB format (P330559, excerpt):

	(DOC
	    (TRANSACTIONS
	      (NUMBER_PRODUCT_LIST
	        (NUMBER_PRODUCT
	          (NUMBERS (NUMBER (COUNT (NU 3))))
	          (PRODUCT
	            (PRODUCT_NAME (COM (N udu)))
	            (PRODUCT_NAME (word (N bar-gal2)))))
	        (NUMBER_PRODUCT
	          (NUMBERS (NUMBER (COUNT (NU 2))))
	          (PRODUCT
	            (PRODUCT_NAME (word (N sila4)))
	            (PRODUCT_NAME (word (N bar-gal2)))))
	        (NUMBER_PRODUCT
	          (NUMBERS (NUMBER (COUNT (NU 1))))
	          (PRODUCT
	            (PRODUCT_NAME (word (N udu)))
	            (PRODUCT_PARAM (word (V bar-su-ga))))))
		  ...
	      (NUMBER_PRODUCT_LIST
	        (NUMBER (COUNT (NU 1)))
	        (NUMBER_PRODUCT
	          (NUMBERS (NUMBER (COUNT (V la2) (NU 1))))
	          (PRODUCT
	            (PRODUCT_NAME (COM (N gu4)))
	            (PRODUCT_PARAM (word (V niga)))
	            (PRODUCT_PARAM (word (V saga)))))
	        (FRAG
	          (NUMBER_PRODUCT
	            (NUMBERS (NUMBER (COUNT (NU 1) (NU 1) (NU 4))))
	            (PRODUCT
	              (PRODUCT_NAME (COM (N gu4)))
	              (PRODUCT_PARAM (word (V niga)))))
	          (UNKNOWN (word (V us2))))
	          ...
	          
CoNLL format (P330559, excerpt):

	3(disz) 3(disz)[one]    NU      NU      D       B-COUNT (DOC (TRANSACTIONS (NUMBER_PRODUCT_LIST (NUMBER_PRODUCT (NUMBERS (NUMBER (COUNT *)))
	udu     udu[sheep]      N       N       D       B-COM   (PRODUCT (PRODUCT_NAME (COM *))
	bar-gal2        bargal[fleeced_sheep]   N       N       D               (PRODUCT_NAME (word *))))
	2(disz) 2(disz)[one]    NU      NU      D       B-COUNT (NUMBER_PRODUCT (NUMBERS (NUMBER (COUNT *)))
	sila4   sila[lamb]      N       N       D               (PRODUCT (PRODUCT_NAME (word *))
	bar-gal2        bargal[fleeced_sheep]   N       N       D               (PRODUCT_NAME (word *))))
	1(disz) 1(disz)[one]    NU      NU      D       B-COUNT (NUMBER_PRODUCT (NUMBERS (NUMBER (COUNT *)))
	udu     udu[sheep]      N       N       D               (PRODUCT (PRODUCT_NAME (word *))
	bar-su-ga       barsuga[without_fleece][-ø]     V       NF.V.ABS        D               (PRODUCT_PARAM (word *)))))
	...
	1(u)    1(u)[ten]       NU      NU      D       B-COUNT (NUMBER_PRODUCT_LIST (NUMBER (COUNT *))
	la2     la[hang][-ø]    V       NF.V.ABS        D       I-COUNT (NUMBER_PRODUCT (NUMBERS (NUMBER (COUNT *
	1(disz) 1(disz)[one]    NU      NU      D       I-COUNT *)))
	gu4     gud[ox] N       N       D       B-COM   (PRODUCT (PRODUCT_NAME (COM *))
	niga    niga[fattened][-ø]      V       NF.V.ABS        D               (PRODUCT_PARAM (word *))
	saga    saga[good][-ø]  V       NF.V.ABS        D               (PRODUCT_PARAM (word *))))
	1(gesz2)        1(gesz)[sixty]  NU      NU      D       B-COUNT (FRAG (NUMBER_PRODUCT (NUMBERS (NUMBER (COUNT *
	1(u)    1(u)[ten]       NU      NU      D       I-COUNT *
	4(disz) 4(disz)[one]    NU      NU      D       I-COUNT *)))
	gu4     gud[ox] N       N       D       B-COM   (PRODUCT (PRODUCT_NAME (COM *))
	niga    niga[fattened][-ø]      V       NF.V.ABS        D               (PRODUCT_PARAM (word *))))
	us2     us[follow][-ø]  V       NF.V.ABS        D               (UNKNOWN (word *)))
	...


Transaction-level legacy parser
==
The repository also maintains an older implementation that is capable of processing *different* input formats, including ATF and plain text. Pre-annotations are optional, these parsers do, however, perform transaction-level parsing only, and they are generally less performant than the document-level parser that requires pre-annotations.

- `jaworski*` files
	- older CFG parser for semantic parsing, independent from preannotations, transaction-level parsing only (no document-level parsing)
		
		`jaworski.cfg` CFG grammar, slightly enriched extraction patterns as defined by Jaworski (2008)

		`jaworski.py` for parsing plain text as extracted from an ATF file, one line at a time. Optimised for speed, not accuracy.

		`jaworski4conll.py` for parsing with pre-annotations (CDLI-CoNLL: tokenization, morphology, CoNLL-U/CDLI-CoNLL: dependency syntax).
		Can process multi-line tokens. Implements a preference ranking over possible start symbols by means of iterated parses with different start symbols. Relatively slow.

	- Experimental conversion to UD dependency labels. This also provides routines to connect all partial analyses into a 
	  single result graph. Note that these "repair operations" are rather slow.

		`jaworski2deps.sh`

	- Workflow demonstration on sample data (for CoNLL and text files)

		`demo.sh`

	Note: For high-precision parsing, we recommend jaworski4conll.py. 
	The primary application of this parser is to mine gold data to train annotators on. It is not optimized for speed,
	but aims to maximize recall while maintaining a maximum level of precision. Therefore, the parser is iteratively applied: 
	To produce partial parses, it re-iterates over the CFG grammar using different start symbols.

	Note: For speed (e.g., in production mode), we recommend jaworski.py.

Acknowledgements
==

Author : Christian Chiarcos, Goethe Unviersität Frankfurt

Developed by the MTAAC project (2017-2020) for the CDLI.
Partially supported by the research group "Linked Open Dictionaries" (LiODi, funded 2015-2020 as an eHumanities research group by the German Federal 
Ministry of Education and Research, BMBF)

The transaction-level CFG parser replicates the semantic parser described by Jaworski 2008 (https://dl.acm.org/doi/10.5555/1599081.1599128), albeit with a different technology.
