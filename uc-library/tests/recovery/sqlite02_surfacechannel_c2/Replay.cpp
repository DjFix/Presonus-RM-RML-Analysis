#include "presonus/surface/SurfaceChannelComponent.hpp"

#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <type_traits>

namespace {
using Subject = Presonus::Surface::SurfaceChannelComponent;
static_assert(std::is_base_of_v<Presonus::UC::ServerComponent, Subject>);
static_assert(std::is_base_of_v<Core::Portable::Component, Subject>);
struct Probe final : Subject {
  explicit Probe(int mode) : Subject(mode) {}
};

int destroyed = 0;
struct Child final : Core::Portable::Component {
  ~Child() override { ++destroyed; }
};

void require(bool condition) {
  if (!condition)
    std::abort();
}
} // namespace

int main(int argc, char **argv) {
  require(argc == 2);
  const int mode = std::atoi(argv[1]);
  unsigned observed = 0;
  {
    Probe probe{mode};
    Presonus::UC::ServerComponent &server = probe;
    Core::Portable::Component &core = server;
    // Canonical roles disable C++ RTTI. Exercise the real Core type query.
    require(Core::Portable::core_cast<Core::Portable::Component>(&core) ==
            &core);
    require(std::strcmp(core.getName(), "") == 0);
    require(core.getParent() == nullptr);
    require(core.countChildren() == 0 && core.countParameters() == 0);
    auto *child = new Child;
    core.addChild(child);
    require(core.getChild(0) == child && child->getParent() == &core);
    observed = probe.channelMode;
    Presonus::Surface::SurfaceChannelComponent oldDefault;
    require(oldDefault.channelMode == 0);
  }
  require(destroyed == 1);
  std::printf("%u\n", observed);
}
