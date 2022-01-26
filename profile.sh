export EPICS_HOST_ARCH=linux-x86_64
export EPICS_BASE=/opt/epics_base
case ":${PATH}:" in
  *:"${EPICS_BASE}/bin/${EPICS_HOST_ARCH}":*)
    ;;
  *)
    PATH="${PATH}:${EPICS_BASE}/bin/${EPICS_HOST_ARCH}"
esac
export PATH
export LD_LIBRARY_PATH="${LD_LIBRARY_PATH}${LD_LIBRARY_PATH+:}$EPICS_BASE/lib/${EPICS_HOST_ARCH}"

export EPICS_CA_ADDR_LIST="127.255.255.255"
export EPICS_CA_AUTO_ADDR_LIST=NO
