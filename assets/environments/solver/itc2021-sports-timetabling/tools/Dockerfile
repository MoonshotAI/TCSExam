# SPDX-License-Identifier: GPL-3.0-or-later
ARG TCSEXAM_BUILDER_IMAGE
FROM ${TCSEXAM_BUILDER_IMAGE} AS builder
ENV DEBIAN_FRONTEND=noninteractive LC_ALL=C
RUN apt-get -o Acquire::Retries=2 update \
 && apt-get -o Acquire::Retries=2 install -y --no-install-recommends make=4.3-4.1build1 g++=4:11.2.0-1ubuntu1 g++-11=11.4.0-1ubuntu1~22.04.3 gcc-11=11.4.0-1ubuntu1~22.04.3 cpp-11=11.4.0-1ubuntu1~22.04.3 libstdc++-11-dev=11.4.0-1ubuntu1~22.04.3 libgcc-11-dev=11.4.0-1ubuntu1~22.04.3 libboost1.74-dev=1.74.0-14ubuntu3 \
 && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY source/ source/
COPY GPL-LICENSE /usr/share/doc/robinx/GPL-LICENSE
RUN g++ -std=c++11 -O2 -static -s -Isource/include source/interface/onlineMain.cpp source/parser/tinyXMLParser.cpp source/parser/tinyxml2.cpp source/validator/ClassConstraint.cpp source/validator/ClassException.cpp source/validator/ClassInstance.cpp source/validator/ClassInterface.cpp source/validator/ClassLeague.cpp source/validator/ClassLeagueGroup.cpp source/validator/ClassMeeting.cpp source/validator/ClassSlot.cpp source/validator/ClassSlotGroup.cpp source/validator/ClassTeam.cpp source/validator/ClassTeamGroup.cpp source/validator/Globals.cpp -pthread -ldl -o /RobinX
RUN printf '%s  %s\n' '476387ba29f555d4fac6ad7855b2efb54bee065c259bf1ac4b59814c016d7bee' '/RobinX' | sha256sum -c -
FROM scratch
COPY --from=builder /RobinX /payload/rootfs/opt/itc2021/RobinX
