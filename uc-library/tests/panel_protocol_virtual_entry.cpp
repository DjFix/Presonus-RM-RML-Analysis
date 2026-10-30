#include "presonus/panel/protocol_comm.hpp"

// Independent fixture boundary, separate TU and no LTO. Invokes the actual
// concrete object's virtual deleting-destructor slot inherited from Protocol.
extern "C" __attribute__((noinline)) void
protocol_delete_concrete(Presonus::Panel::ProtocolComm *object) {
  delete object;
}
