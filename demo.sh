#!/bin/bash
PYTHON=python3.7

# transaction parsing with various pre-annotations
# supports both parsing plain text/atf files and CDLI-CoNLL/CoNLL-U files for pre-annotated text
# conll mode requires the processed files to end in *.conll[^\.]*
# text/atf mode is optimized for speed, conll mode for quality

################
# sample input #
################
# with different kinds of pre-annotation

# the path should NOT contain path separators
# the directory should contain only input files
INPUT=input

# input as ATF file (no annotations)
ATF=$INPUT/atf

# input as plain text, with one line per sentence
TEXT=$INPUT/text

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

for file in `find $INPUT`; do
	if [ -f $file ]; then
		dir=`echo $file | sed s/'\/[^\/]*$'//g;`
		dir=$OUTPUT`echo $dir | sed s/'^'$INPUT//g`
		if [ ! -e $dir ]; then 
			echo create $dir 1>&2
			mkdir -p $dir ; 
		fi;

		if echo $file | egrep 'comm.*conll$' >& /dev/null; then
			echo $file': parsing in CoNLL mode with MTAAC COMM preannotations' 1>&2
			PARSER="parse_comm.py --ptb"
		else
			if echo $file | egrep 'conll$' >&/dev/null; then
				echo $file': parsing in CoNLL mode' 1>&2
				echo '(to enable COMM parser, use a path or file name that contains the string comm)' 1>&2
				PARSER=jaworski4conll.py
			else
				echo $file': parsing in plain text mode' 1>&2
				PARSER=jaworski.py
			fi;
		fi;

		# CFG parsing
		id=`basename $file | sed s/'\..*'//g`
		out=$dir/$id.psd;
		echo -n CFG parsing: $file "=>" $out" " 1>&2
		if [ -s $out ]; then
			echo "skipped (file found)" 1>&2
		else
			time ($PYTHON $PARSER $file > $out) 1>&2
			if [ -s $out ]; then
				echo "ok" 1>&2
			else
				echo "failed" 1>&2
			fi
		fi
		echo 1>&2

		# UD export (experimental)
		dir=$EXPORT`echo $dir | sed s/'^'$OUTPUT//g`
		if [ ! -e $dir ]; then
			mkdir -p $dir;
		fi;

		# file-by-file processing is slow, concatenate to speed up
		tgt=$dir/$id.conll
		echo -n UD conversion: $out "=>" $tgt" " 1>&2;
		if [ -s $tgt ]; then
			echo "skipped (file found)" 1>&2
		else
			time (bash -e jaworski2deps.sh $out > $tgt 2>$tgt.log) 1>&2
			if [ -s $tgt ]; then
				echo ok 1>&2
			else 
				echo failed 1>&2
			fi;
		fi;
		echo 1>&2
		if [ ! -s $tgt ]; then
			cat $tgt.log 1>&2;
			echo 1>&2
		else
			rm $tgt.log;
		fi;
	fi;
done;
echo done 1>&2
