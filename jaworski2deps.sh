#!/bin/bash

#
# CONFIG
########

# set to your CoNLL-RDF home or get it from https://github.com/acoli-repo/conll-rdf
CONLL=~/conll-rdf

#
# PREP
######


#LOAD=$CONLL/run.sh" CoNLLStreamExtractor http://ignore.me/ WORD PARSE"
LOAD=$CONLL/run.sh" CoNLLBrackets2RDF http://ignore.me/ WORD PARSE"
TRANSFORM=$CONLL/run.sh" CoNLLRDFUpdater -custom -updates"
WRITE=$CONLL/run.sh" CoNLLRDFFormatter "

#
# RUN
######

for file in $*; do

	# PSD 2 CoNLL
	echo '# '$file;
	cat $file | sed s/'\#.*'// | egrep '.' |\
	perl -pe '
		s/\s+/ /g;
		s/\)\s*\(/\)\n\(/g;
	' | \
	perl -pe '
		s/  +/ /g;
		s/\( */\(/g;
		s/ *\) /\)/g;
		s/(\([^\s\[]+)\|[^()\s]+/$1/g;
		s/\)\s*\(/\)\n\(/g;
	' | \
	perl -pe '
		s/(.*\([^ ()]+) ([^()]+|[^()]+\([^()]*\)[^()]*)(\))/$2\t$1 *$3/g;

	';
	echo;
	echo
done | \
\
	# # DEBUG mode
# head -n 100 | \
\
# CoNLL2DEPS
$LOAD | \
$TRANSFORM \
	consolidate-parse.sparql \
	parse2psd.sparql \
	parse2dep.sparql \
	dep2ud.sparql \
	| \
$WRITE -conll ID WORD LEMMA UPOS XPOS FEATS HEAD EDGE DEPS PSD
