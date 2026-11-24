#include "presonus/surface/MainScreenComponent.hpp"
#include <cstdio>

#include "presonus/surface/MappingComponent.hpp"

namespace Presonus::Surface {
struct MainScreenComponentReplayAccess {
  static MappingComponent *mapping(const MainScreenComponent &screen) {
    return screen.mapping_;
  }
};
} // namespace Presonus::Surface

class Application : public presonus::mainlcd_port::Application {
public:
  Presonus::PageComponent *findPage(int) const override { return nullptr; }
  void requestPage(Presonus::PageComponent *) override {}
  void showNextPage() override {}
  int startPageTag() const override { return 0; }
  Core::Portable::RootView *rootView(Presonus::LcdView *) const override {
    return nullptr;
  }
  void observeView(Presonus::LcdView *, Presonus::MainLCDComponent &) override {
  }
};

class Mapping : public Presonus::Surface::MappingComponent {
public:
  Mapping() : MappingComponent(presonus::surface::MappingRouteInit{}) {}
  bool isDisplayEncoderLocked() const override { return false; }
  void selectedChannelUpdated() override {}
};

int main() {
  using namespace Presonus::Surface;
  Application app;
  presonus::mainlcd_port::State state;
  MainScreenComponent screen(presonus::surface::MainScreenInit{}, app, state);
  Mapping first;
  Mapping second;
  MappingComponent *const values[] = {nullptr, &first, &second};
  const auto code = [&](const MappingComponent *pointer) {
    return pointer == nullptr   ? 0u
           : pointer == &first  ? 1u
           : pointer == &second ? 2u
                                : 3u;
  };
  const unsigned sequence[] = {1, 2, 0, 1};
  for (unsigned index : sequence) {
    const auto before = code(MainScreenComponentReplayAccess::mapping(screen));
    screen.init(values[index]);
    std::printf("%u %u %u\n", index, before,
                code(MainScreenComponentReplayAccess::mapping(screen)));
  }
}
