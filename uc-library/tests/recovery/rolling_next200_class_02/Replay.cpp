#include "presonus/link/Messenger.hpp"
#include <array>
#include <cstdio>
#include <cstring>

namespace {
using Presonus::Link::Messenger;

using ObjectBytes = std::array<unsigned char, sizeof(Messenger)>;

bool observe(Messenger &receiver, bool released) {
  if (released)
    receiver.release();
  ObjectBytes before{}, after{};
  std::memcpy(before.data(), &receiver, before.size());
  const bool state = receiver.releaseRequested();
  receiver.init();
  std::memcpy(after.data(), &receiver, after.size());
  const bool unchanged =
      before == after && state == receiver.releaseRequested();
  std::printf("case %d %d\n", released, unchanged);
  return state == released && unchanged;
}
} // namespace

int main() {
  Messenger fresh;
  Messenger released;
  const bool freshUnchanged = observe(fresh, false);
  const bool releasedUnchanged = observe(released, true);
  return freshUnchanged && releasedUnchanged ? 0 : 1;
}
