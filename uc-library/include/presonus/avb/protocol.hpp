#pragma once

namespace Presonus::DICE {
class SysexPacket;
}
namespace presonus::avb {
struct ReceiveContext;
}

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

  // Portable pointer return choices; exact original return spelling unresolved.
  AvbListener *findListener(unsigned char identifier);
  AvbTalker *findTalker(unsigned char identifier);
  unsigned char lookupNextTalkerIndex();

  // Independent portable setup; no original constructor claim.
  void bindReceiveContext(presonus::avb::ReceiveContext &context) {
    receiveContext_ = &context;
  }

private:
  presonus::avb::ReceiveContext *receiveContext_ = nullptr;
};
} // namespace Presonus::AVB
