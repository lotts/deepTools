#!/usr/bin/env python
#-*- coding: utf-8 -*-

import numpy as np
import argparse
from matplotlib import use as mplt_use
mplt_use('Agg')
import matplotlib.pyplot as plt

import deeptools.countReadsPerBin as countR
from deeptools import parserCommon


def parse_arguments(args=None):
    parent_parser = parserCommon.getParentArgParse(binSize=False)
    required_args = get_required_args()
    output_args = get_output_args()
    optional_args = get_optional_args()
    read_options_parser = parserCommon.read_options()
    parser = argparse.ArgumentParser(
        parents=[required_args, output_args, read_options_parser,
                 optional_args, parent_parser],
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
        description='Samples indexed bam files '
        'and plots a profile for each bam file. '
        'At each sample position all reads '
        'overlapping a window (bin) of '
        'specified length are counted. '
        'These counts are then sorted '
        'and the cumulative sum plotted ',
        conflict_handler='resolve',
        usage='An example usage is: %(prog)s -b treatment.bam control.bam '
        '-o signal.b',
        add_help=False)

    return parser


def process_args(args=None):

    args = parse_arguments().parse_args(args)

    if args.labels and len(args.bamfiles) != len(args.labels):
        print "The number of does not match the number of bam files."
        exit(0)

    args.extendPairedEnds = False if args.doNotExtendPairedEnds else True

    if not args.labels:
        args.labels = args.bamfiles

    return args


def get_required_args():
    parser = argparse.ArgumentParser(add_help=False)
    required = parser.add_argument_group('Required arguments')

    # define the arguments
    required.add_argument('--bamfiles', '-b',
                          metavar='bam files',
                          nargs='+',
                          help='List of sorted Bam files',
                          required=True)
    return parser


def get_optional_args():
    parser = argparse.ArgumentParser(add_help=False,
                                     conflict_handler='resolve')
    optional = parser.add_argument_group('Optional arguments')
    optional.add_argument("--help", "-h", action="help",
                          help="show this help message and exit")

    optional.add_argument('--labels', '-l',
                          metavar='',
                          help='List of labels to use in the output. '
                          'If not given the file names will be used instead. '
                          'Separate the labels by space.',
                          nargs='+')

    optional.add_argument('--binSize', '-bs',
                          help='Length in base pairs for a window used to '
                          'sample the genome.',
                          default=500,
                          type=int)

    optional.add_argument('--fragmentLength', '-f',
                          help='Length of the average fragment size.',
                          type=int,
                          default=200)

    optional.add_argument('--numberOfSamples', '-n',
                          help='Number of bins, sampled from the genome '
                          'to compute the average number of reads.',
                          default=5e5,
                          type=int)

    optional.add_argument('--plotFileFormat',
                          metavar='',
                          help='image format type. If given, this option '
                          'overrides the image format based on the plotFile '
                          'ending. The available options are: "png", "emf", '
                          '"eps", "pdf" and "svg"',
                          choices=['png', 'pdf', 'svg', 'eps', 'emf'])

    optional.add_argument('--plotTitle', '-T',
                          help='Title of the plot, to be printed on top of '
                          'the generated image. Leave blank for no title.',
                          default='')

    optional.add_argument('--skipZeros',
                          help='If set, then zero counts that happen '
                          'for *all* bam files given are ignored. This '
                          'will result in a reduced number of read '
                          'counts than the the specified in --numberOfSamples',
                          action='store_true')

    return parser


def get_output_args():
    parser = argparse.ArgumentParser(add_help=False)
    group = parser.add_argument_group('Output')
    group.add_argument('--plotFile', '-plot',
                       help='File name of the output figure. The file '
                       'ending  will be used to determine the image '
                       'format. The available options are: "png", "emf", '
                       '"eps", "pdf" and "svg", e.g. : fingerprint.png.',
                       metavar='',
                       type=argparse.FileType('w'),
                       required=True)

    group.add_argument('--outRawCounts',
                       help='Output file name to save the bin counts',
                       metavar='',
                       type=argparse.FileType('w'))

    return parser


def main(args=None):
    args = process_args(args)

    cr = countR.CountReadsPerBin(
        args.bamfiles,
        args.binSize,
        args.numberOfSamples,
        args.fragmentLength,
        numberOfProcessors=args.numberOfProcessors,
        verbose=args.verbose,
        region=args.region,
        extendPairedEnds=args.extendPairedEnds,
        minMappingQuality=args.minMappingQuality,
        ignoreDuplicates=args.ignoreDuplicates,
        center_read=args.centerReads,
        samFlag_include=args.samFlagInclude,
        samFlag_exclude=args.samFlagExclude)

    num_reads_per_bin = cr.run()
    if num_reads_per_bin.sum() == 0:
        import sys
        sys.stderr.write(
            "\nNo reads were found in {} regions sampled. Check that the\n"
            "min mapping quality is not overly high and that the \n"
            "chromosome names between bam files are consistant.\n"
            "\n".format(num_reads_per_bin.shape[0]))
        exit(1)

    if args.skipZeros:
        num_reads_per_bin = countR.remove_row_of_zeros(num_reads_per_bin)

    total = len(num_reads_per_bin[:, 0])
    x = np.arange(total).astype('float') / total  # normalize from 0 to 1

    i = 0
    for reads in num_reads_per_bin.T:
        count = np.cumsum(np.sort(reads))
        count = count / count[-1]  # to normalyze y from 0 to 1
        plt.plot(x, count, label=args.labels[i])
        plt.xlabel('rank')
        plt.ylabel('fraction w.r.t. bin with highest coverage')
        i += 1
    plt.legend(loc='upper left')
    plt.suptitle(args.plotTitle)
    # set the plotFileFormat explicitly to None to trigger the
    # format from the file-extension
    if not args.plotFileFormat:
        args.plotFileFormat = None

    plt.savefig(args.plotFile.name, bbox_inches=0, format=args.plotFileFormat)

    if args.outRawCounts:
        args.outRawCounts.write("'" + "'\t'".join(args.labels) + "'\n" )
        fmt = "\t".join(np.repeat('%d', num_reads_per_bin.shape[1])) + "\n"
        for row in num_reads_per_bin:
            args.outRawCounts.write(fmt % tuple(row))

if __name__ == "__main__":
    main()
