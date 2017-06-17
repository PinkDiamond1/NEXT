FROM ubuntu:14.04
MAINTAINER "Kwame Porter Robinson" kporterrobinson@gmail.com

RUN apt-get -y install git gcc-c++ make boost-devel zlib-devel clang-devel which &&\
    git clone git://github.com/JohnLangford/vowpal_wabbit.git /vowpal_wabbit &&\
    cd /vowpal_wabbit && make && make install &&\
    rm -Rf /vowpal_wabbit/* && apt-get -y remove git gcc-c++ make boost-devel zlib-devel clang-devel which &&\
    apt-get autoremove

#WORKDIR /vowpal_wabbit
#COPY run.sh /vowpal_wabbit
#RUN chmod a+x run.sh
#ENTRYPOINT ["/vowpal_wabbit/run.sh"]
