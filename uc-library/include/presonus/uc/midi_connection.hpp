#pragma once

#include <cstdint>

namespace Presonus::UC {
// Independent portable value layout, not the original 20-byte ARM structure.
// App dispatch/input-adapter accesses establish these value roles, not their
// original field names or pointer const qualification. The size word stays 20
// because that is the observed application value, not sizeof this port.
struct MidiEvent {
  std::uint32_t portableSizeWord = 20;
  std::uint32_t messageWord = 0;
  const unsigned char *sysexData = nullptr;
  std::uint16_t sysexLength = 0;
  std::uint32_t trailingWord = 0;
};

// Original RTTI and the concrete UCMidiInputAdapter vtable establish a
// base-free, single-callback interface without a virtual destructor. The void
// return spelling is an explicit source-port choice: MidiConnection ignores
// the callback's original return register. Original return spelling is pending.
class IMidiEventHandler {
public:
  virtual void handleMidiEvent(const MidiEvent &event) = 0;
};

// Original RTTI establishes no bases; its vtable has D1, D0 and deliver slots.
// Native pointer width/layout and C1/C2 aliasing are distinct from ARM32.
class MidiConnection {
public:
  MidiConnection();
  virtual ~MidiConnection();
  // Observed results are 0/1; original bool versus integer spelling is pending.
  virtual bool deliver(const MidiEvent &event);

  // Independent borrowed setup, not an invented original ELF method.
  void setPortableHandler(IMidiEventHandler *handler) { handler_ = handler; }
  IMidiEventHandler *portableHandler() const { return handler_; }

private:
  IMidiEventHandler *handler_;
};
} // namespace Presonus::UC
