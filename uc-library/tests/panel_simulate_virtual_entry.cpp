#include "presonus/panel/protocol_comm.hpp"
extern "C" void simulate_virtual_delete(Presonus::Panel::ProtocolComm *value) {
  delete value;
}
extern "C" void simulate_virtual_destroy(Presonus::Panel::ProtocolComm *value) {
  value->~ProtocolComm();
}
