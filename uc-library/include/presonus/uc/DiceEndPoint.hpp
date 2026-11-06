#pragma once
#include "presonus/uc/DataChannel.hpp"
namespace Core::IO {
class Stream;
}
namespace Presonus::UC {
class DicePacketQueue;
// Portable source model: borrows both real queue providers. Original ARM
// fields, ordinary return declarations and binary interoperability remain
// unresolved.
class DiceEndPoint : public DataChannel {
public:
  DiceEndPoint(DicePacketQueue &incoming, DicePacketQueue &outgoing);
  ~DiceEndPoint() override;
  // Source-port return choice. Streams must terminate each pass with zero and
  // supply initialized bytes for every uint8-truncated nonzero read result,
  // including negative results. Requests wrap through zero as in the native
  // code. Queue factory allocation must succeed; all providers outlive this
  // object.
  void test(Core::IO::Stream &stream);

private:
  DicePacketQueue &incomingQueue_, &outgoingQueue_;
};
} // namespace Presonus::UC
