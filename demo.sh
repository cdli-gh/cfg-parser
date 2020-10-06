#!/bin/bash
PYTHON=python3.7

# transaction parsing with various pre-annotations
# for parsing from plain text, use jaworski.py

################
# sample input #
################
# with different kinds of pre-annotation

# should NOT contain path separators
INPUT=input

# plain text in CoNLL format
# full data under https://github.com/cdli-gh/mtaac_cdli_ur3_corpus/tree/master/ur3_corpus_data/conll
PLAIN=$INPUT/plain

# morphology with MTAAC gold annotations
# full data under https://github.com/cdli-gh/mtaac_gold_corpus/tree/workflow/morph/to_dict
MORPH=$INPUT/morph

# syntax preannotated (over manual morphology)
# full data under https://github.com/cdli-gh/MTAAC_syntax_preannotated
SYNTAX=$INPUT/syntax

##########
# output #
##########
# should NOT contain path separators

OUTPUT=psd
EXPORT=conll

###############
# CFG parsing #
###############

for file in `find $INPUT | grep 'conll$'`; do
	dir=`echo $file | sed s/'\/[^\/]*$'//g;`
	dir=$OUTPUT/`echo $dir | sed s/'^'$INPUT//g`
	if [ ! -e $dir ]; then 
		echo create $dir 1>&2
		mkdir -p $dir ; 
	fi;


	# CFG parsing
	id=`basename $file | sed s/'\..*'//g`
	out=$dir/$id.psd;
	echo CFG parsing "(disable partial parsing for speeding up)": $file "=>" $out 1>&2
	$PYTHON jaworski4conll.py $file > $out

	# UD export (experimental)
	dir=$EXPORT/`echo $dir | sed s/'^'$OUTPUT//g`
	if [ ! -e $dir ]; then
		mkdir -p $dir;
	fi;

	# file-by-file processing is slow, concatenate to speed up
	tgt=$dir/$id.conll
	echo UD conversion: $out "=>" $tgt 1>&2;
	(bash -e jaworski2deps.sh $out > $tgt 2>$tgt.log)
	if [ ! -s $tgt ]; then
		cat $tgt.log 1>&2;
		echo 1>&2
	else
		rm $tgt.log;
	fi;
done;
echo done 1>&2
