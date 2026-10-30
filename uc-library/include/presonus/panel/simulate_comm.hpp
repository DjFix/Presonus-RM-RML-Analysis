#pragma once
#include "presonus/panel/protocol_comm.hpp"
#include <cstdint>

namespace presonus::panel {
struct SimulateCommAccess;
}
namespace Presonus::Panel {
// Original shared class/virtual identities, with portable storage. Ordinary
// return spelling and static-field C++ declarations remain evidence-limited;
// this is not the ARM32 object layout or a concurrent endpoint guarantee.
class SimulateComm : public ProtocolComm {
public:
  explicit SimulateComm(bool);
  ~SimulateComm() override;
  int open(const char *) override;
  void close() override;
  int enableHISpeed(bool) override;
  int write(const char *, int) override;
  int read(char *, int) override;

private:
  char *readBuffer_ = nullptr;
  char *writeBuffer_ = nullptr;
  static char *s_buffer1;
  static char *s_buffer2;
  static std::uint32_t s_instances;
  friend struct presonus::panel::SimulateCommAccess;
};
} // namespace Presonus::Panel

namespace presonus::panel {
// Independent bounded fixture access, not an original application interface.
struct SimulateCommAccess {
  static char *first() { return Presonus::Panel::SimulateComm::s_buffer1; }
  static char *second() { return Presonus::Panel::SimulateComm::s_buffer2; }
  static std::uint32_t instances() {
    return Presonus::Panel::SimulateComm::s_instances;
  }
  static void shared(char *a, char *b, std::uint32_t count) {
    Presonus::Panel::SimulateComm::s_buffer1 = a;
    Presonus::Panel::SimulateComm::s_buffer2 = b;
    Presonus::Panel::SimulateComm::s_instances = count;
  }
  static void endpoints(Presonus::Panel::SimulateComm &v, char *a, char *b) {
    v.readBuffer_ = a;
    v.writeBuffer_ = b;
  }
  static char *input(Presonus::Panel::SimulateComm &v) { return v.readBuffer_; }
  static char *output(Presonus::Panel::SimulateComm &v) {
    return v.writeBuffer_;
  }
};
} // namespace presonus::panel
