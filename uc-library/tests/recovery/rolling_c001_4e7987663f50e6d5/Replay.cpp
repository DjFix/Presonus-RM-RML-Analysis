#include "presonus/surface/CapturePageComponent.hpp"
#include <array>
#include <cstdio>
#include <cstring>

// Opaque fixture object: only its reference identity is passed.
namespace Presonus {
class DAWClientComponent {
public:
  unsigned char marker = 17;
};
} // namespace Presonus

template <typename T> auto snapshot(const T &object) {
  std::array<unsigned char, sizeof(T)> bytes;
  std::memcpy(bytes.data(), &object, bytes.size());
  return bytes;
}

int main() {
  using namespace Presonus;
  for (unsigned index = 0; index < 3; ++index) {
    IDAWComponentObserver observer;
    Presonus::DAWClientComponent argument[3];

    const auto before = snapshot(observer);
    auto oldArgument = snapshot(argument);
    observer.destroyed(argument[index]);
    if (!(before == snapshot(observer) && oldArgument == snapshot(argument)))
      return 2;
    std::printf("%u 0 0\n", index);
  }
}
