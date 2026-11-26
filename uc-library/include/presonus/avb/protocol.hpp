#pragma once
#include "core/public/corestringbuffer.h"

namespace Presonus::DICE {
class SysexPacket;
}
namespace Presonus::NOAA {
class SysexPacket;
}
namespace presonus::avb {
struct ReceiveContext;
class ManagerTransport;
} // namespace presonus::avb

namespace Presonus::AVB {
class AvbListener;
class AvbTalker;
// Isolated extension of the portable subset, not the old complete object ABI.
class AvbManagerBase {
public:
  virtual bool accepts(const DICE::SysexPacket &packet);
  int unpackAvbSpiMsg(unsigned char *destination, const unsigned char *source,
                      int length);
  unsigned long long reverseEndian(unsigned long long value);
  void char2Nibble(const unsigned char *source, unsigned char *destination,
                   int length);
  void nibble2Char(const unsigned char *source, unsigned char *destination,
                   int length);

  // Candidate void declaration: original receive return remains unresolved.
  virtual void receive(const DICE::SysexPacket &packet);
  // Independent value adapter; original NOAA return declaration is unresolved.
  virtual void receive(const NOAA::SysexPacket &packet);

  // Portable pointer return choices; exact original return spelling unresolved.
  AvbListener *findListener(unsigned char identifier);
  AvbTalker *findTalker(unsigned char identifier);
  unsigned char lookupNextTalkerIndex();

  // Portable count declarations. Original return spelling and virtuality
  // remain unresolved.
  // Source-port return choices; exact original ordinary declarations pending.
  void removeListener(AvbListener *listener);
  int resizeListener(unsigned char identifier, unsigned char channels);
  int setAudioClockToListener(AvbListener *listener);
  AvbListener *addListener(unsigned long long identifier, unsigned short suffix,
                           unsigned char channels);
  int resizeTalker(unsigned char identifier, unsigned char channels);
  void removeTalker(AvbTalker *talker);
  AvbTalker *addTalker(unsigned char channels);
  int publish(unsigned char identifier, bool enabled);
  int sendAvbSysex(unsigned char command, unsigned char *payload, int length);
  // ARM arguments prove these helpers have no this argument. Return spelling
  // and upper16 parser return bits remain unresolved; the port initializes
  // them.
  static unsigned long long macAddressStringToLong(Core::CString256 &text);
  static void macAddressToString(Core::CString256 &text,
                                 unsigned long long value);
  int subscribe(unsigned char identifier, unsigned long long streamKey);
  void removeAllListeners();
  int startAvb(unsigned char first, unsigned char second, bool enabled);
  int configureMasterFirewireRecording(bool enabled);
  void stopAvb();
  virtual bool accepts(const NOAA::SysexPacket &packet);

  // Borrowed initialized real receiver/transport composition; setup only.
  void bindTransport(presonus::avb::ManagerTransport &transport);
  int numActiveListeners();
  int numFreeListeners();
  int numFreeTalkers();

  enum class Role { Cs18Client, RmServer };

  // Independent portable setup; no original constructor claim. A receive-only
  // binding clears role configuration. Free-count queries require a role.
  void bindReceiveContext(presonus::avb::ReceiveContext &context, Role role);

  // Independent portable setup; no original constructor claim.
  void bindReceiveContext(presonus::avb::ReceiveContext &context) {
    receiveContext_ = &context;
    streamCapacity_ = 0;
  }

private:
  friend class presonus::avb::ManagerTransport;
  int streamCapacity() const;
  presonus::avb::ManagerTransport *transport_ = nullptr;
  int streamCapacity_ = 0;
  presonus::avb::ReceiveContext *receiveContext_ = nullptr;
};
} // namespace Presonus::AVB
