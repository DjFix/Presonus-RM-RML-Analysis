#include "presonus/avb/AvbComponent.hpp"
#include <cstdarg>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <new>
#include <string>
#include <vector>
using Presonus::AVB::AvbComponent;
static void *watched = nullptr;
static bool deallocated = false;
void operator delete(void *p) noexcept {
  if (p == watched)
    deallocated = true;
  std::free(p);
}
void operator delete(void *p, std::size_t) noexcept { ::operator delete(p); }
struct Recorder : presonus::avb::ListenerServices {
  std::vector<std::string> events;
  presonus::avb::Listener *addListener(unsigned long long, unsigned short,
                                       unsigned char) override {
    std::abort();
  }
  void removeListener(presonus::avb::Listener *) override { std::abort(); }
  void setAudioClockToListener(presonus::avb::Listener *) override {
    std::abort();
  }
  void configureStaticTalkerStreams() override { std::abort(); }
  void routeLinkSlotsFromAvb() override { std::abort(); }
  void sendRoutingPacket(const presonus::avb::RoutingPacket &p) override {
    std::string s = "[\"packet\",[";
    for (std::size_t i = 0; i < 6; ++i) {
      if (i)
        s += ",";
      s += std::to_string(p.words[i]);
    }
    if (p.words[1] == 28)
      s += "," + std::to_string(p.enabled ? 1 : 0);
    events.push_back(s + "]]");
  }
};
static Recorder *active = nullptr;
extern "C" void real_debug(const char *,
                           ...) asm("__real__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrap_debug(const char *format,
                           ...) asm("__wrap__ZN4Core11DebugPrintfEPKcz");
extern "C" void wrap_debug(const char *format, ...) {
  va_list ap;
  va_start(ap, format);
  int index = va_arg(ap, int);
  va_end(ap);
  if (active)
    active->events.push_back("[\"debug\"," + std::to_string(index) + "]");
  real_debug(format, index);
}
extern "C" void
real_remove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__real__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void
wrap_remove(Core::Portable::Parameter *, Core::Portable::IParamObserver *) asm(
    "__wrap__ZN4Core8Portable9Parameter14removeObserverEPNS0_"
    "14IParamObserverE");
extern "C" void wrap_remove(Core::Portable::Parameter *p,
                            Core::Portable::IParamObserver *o) {
  if (active)
    active->events.push_back("[\"remove_observer\"]");
  real_remove(p, o);
}
struct Resource : presonus::avb::ComponentResource {
  Recorder &r;
  explicit Resource(Recorder &r) : r(r) {}
  void release() override { r.events.push_back("[\"release\"]"); }
};
struct Child : Core::Portable::Component {
  Recorder &r;
  explicit Child(Recorder &r) : r(r) {}
  ~Child() override { r.events.push_back("[\"core_cleanup\"]"); }
};
extern "C" void avb_d2(void *) asm("_ZN8Presonus3AVB12AvbComponentD2Ev");
extern "C" void server_d2(void *) asm("_ZN8Presonus2UC15ServerComponentD2Ev");
int main(int argc, char **argv) {
  if (argc < 2)
    return 2;
  std::string kind = argv[1];
  Recorder r;
  Resource resource(r);
  presonus::avb::Listener listener{17};
  presonus::avb::ListenerState state{};
  state.consoleSource = 0x98765432;
  std::uint32_t mode = 0;
  if (kind == "destructor") {
    if (argc != 4)
      return 2;
    auto address = std::stoul(argv[2]);
    bool present = std::stoi(argv[3]);
    state.resource = present ? &resource : nullptr;
    if (address == 0x1cfe8) {
      void *mem = ::operator new(sizeof(Presonus::UC::ServerComponent));
      auto *c = new (mem) Presonus::UC::ServerComponent();
      c->addChild(new Child(r));
      server_d2(c);
      ::operator delete(mem);
    } else if (address == 0xa8e88) {
      auto *c = new AvbComponent(state, r);
      c->addChild(new Child(r));
      watched = c;
      delete c;
      watched = nullptr;
      if (!deallocated)
        return 3;
      r.events.push_back("[\"delete\"]");
    } else {
      void *mem = ::operator new(sizeof(AvbComponent));
      auto *c = new (mem) AvbComponent(state, r);
      c->addChild(new Child(r));
      if (address == 0xa8e0c)
        avb_d2(c);
      else
        c->~AvbComponent();
      ::operator delete(mem);
    }
  } else {
    AvbComponent c(state, r);
    if (kind == "static") {
      state.linkMode = std::stoi(argv[2]);
      c.configureStaticTalkerStreams();
    } else if (kind == "route") {
      bool present = std::stoi(argv[2]);
      listener.index = static_cast<std::uint8_t>(std::stoi(argv[3]));
      state.cascade = present ? &listener : nullptr;
      active = &r;
      c.routeLinkSlotsFromAvb();
      active = nullptr;
    } else if (kind == "spectrum")
      c.setSpectrumDataTxSource(std::stoi(argv[2]), std::stoi(argv[3]));
    else
      return 2;
    mode = static_cast<std::uint32_t>(state.linkMode);
  }
  std::cout << "{\"trace\":[";
  for (std::size_t i = 0; i < r.events.size(); ++i) {
    if (i)
      std::cout << ',';
    std::cout << r.events[i];
  }
  std::cout << "],\"mode\":" << mode << "}\n";
}
