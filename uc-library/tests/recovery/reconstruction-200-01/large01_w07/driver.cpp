#include "presonus/surface/ScribbleStripController.hpp"
#include "presonus/surface/SurfaceChannelComponent.hpp"
#include "presonus/surface/SurfaceInputComponent.hpp"
#include "presonus/surface/SurfaceOutputComponent.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
namespace {
int destroyed = 0;
struct Child : Core::Portable::Component {
  ~Child() override { ++destroyed; }
};
} // namespace
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  using namespace Presonus::Surface;
  if (std::strcmp(argv[1], "cleanup") == 0) {
    {
      SurfaceChannelComponent c;
      c.addChild(new Child);
    }
    {
      SurfaceInputComponent c;
      c.addChild(new Child);
    }
    std::printf("%d\n", destroyed);
    return destroyed == 2 ? 0 : 1;
  }
  if (argc < 3)
    return 2;
  unsigned long v = std::strtoul(argv[2], nullptr, 0);
  if (std::strcmp(argv[1], "output") == 0) {
    SurfaceOutputComponent c;
    c.channelMode = v;
    std::printf("%u\n", c.levelAdjustable());
  } else if (std::strcmp(argv[1], "input") == 0) {
    SurfaceInputComponent c;
    c.channelMode = v;
    std::printf("%u\n", c.levelAdjustable());
  } else if (std::strcmp(argv[1], "lookup") == 0) {
    SurfaceInputComponent c;
    unsigned bits = v;
    float x;
    std::memcpy(&x, &bits, 4);
    std::printf("%u\n", c.lookupPotSetting(x));
  } else
    return 2;
}
