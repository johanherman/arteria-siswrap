# Idea is to have general dependencies from parent image and specific
# dependencies here. Then for testing we install the software via
# running the container instead on the host mounted drives.

FROM arteria/dependencies:1
LABEL Description="Test image for siswrap service" Version="0.1"

# siswrap service dependencies
RUN yum install -y dos2unix gnuplot PyXML ImageMagick libxslt-devel libxml2-devel libxml2-devel ncurses-devel libtiff-devel bzip2-devel zlib2-devel perl-XML-LibXML perl-XML-LibXML-Common perl-XML-NamespaceSupport perl-XML-SAX perl-XML-Simple zlib-devel perl-Archive-Zip perl-CPAN git perl-PDL perl-PerlIO-gzip

#ENV ARTERIA_TEST=1

# We need to open up the ports that the container needs to expose
# We don't really need to do this here though, it is mostly for linking
# containers, or when we want to map them with -P, but we want to use
# -p to get specific mappings at run time for the container.
EXPOSE 10900

#COPY build_data/install_services /root/install_services

# Temporary workaround to match the test runfolders
RUN ln -s /data/150326_150116_M00485_0183_000000000-ABGT6_testbio10 /data/testarteria1/mon1/runfolder_inttest_1437474276963
# Temporary copy of QC config
COPY ~/repod/sisyphus/sisyphus_qc.xml /srv/qc_config/sisyphus_qc.xml

# Start the serviced that takes care of our processes
#CMD service supervisord start
