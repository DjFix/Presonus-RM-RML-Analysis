#include "presonus/uc/DiceEndPoint.hpp"
#include "core/public/corestream.h"
#include "presonus/uc/DicePacketQueue.hpp"
#include <cstring>
namespace Presonus::UC {
DiceEndPoint::DiceEndPoint(DicePacketQueue &incoming, DicePacketQueue &outgoing)
    : DataChannel(incoming, outgoing), incomingQueue_(incoming),
      outgoingQueue_(outgoing) {}
// Native D1 only transitions to the DataChannel table; it does not flush or own
// either queue. C++ performs its real base destruction here; D0 is compiler
// generated and invokes operator delete. Host D2 has no selected native credit.
DiceEndPoint::~DiceEndPoint() = default;
void DiceEndPoint::test(Core::IO::Stream &stream) {
  unsigned char source[256];
  unsigned char midi[256];
  unsigned char destination[256];
  unsigned char length = 4;
  int count;
  while ((count = stream.readBytes(source, length)) != 0) {
    if (count != length)
      length = static_cast<unsigned char>(count);
    outgoingQueue_.write(reinterpret_cast<const char *>(source), length);
    ++length;
  }
  length = 4;
  while (outgoingQueue_.peakMIDI(midi, length)) {
    unsigned char readLength = length;
    outgoingQueue_.readMIDI(midi, readLength);
    incomingQueue_.writeMIDI(midi);
    ++length;
  }
  length = 1;
  stream.setPosition(0, Core::IO::kSeekSet);
  while ((count = stream.readBytes(source, length)) != 0) {
    if (count != length)
      length = static_cast<unsigned char>(count);
    std::memset(destination, 0xfe, sizeof(destination));
    read(destination, length);
    ++length;
    std::memset(source, 0xff, sizeof(source));
  }
  outgoingQueue_.flush();
  incomingQueue_.flush();
}
} // namespace Presonus::UC
