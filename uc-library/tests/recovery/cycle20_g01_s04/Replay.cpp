#include "presonus/surface/sl_mixer_encoder.hpp"

#include <cstddef>
#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {
const void *receiver;

void require(bool condition) {
  if (!condition)
    std::abort();
}

class HandlerFixture final : public Presonus::AssignmentHandler {
public:
  const char *getName() const override { return "fixture"; }
  void updateConnections() override {}
};

class MixerHandlerFixture final : public Presonus::MixerAssignmentHandler {
public:
  const char *getName() const override { return "fixture"; }
  void updateConnections() override {}
  void onMappingParamChanged(Core::Portable::Parameter *) override {}
  bool getParamFocusInfo(FocusInfo &, Core::Portable::Parameter *) override {
    return false;
  }
};

template <typename Base, typename Fixture> Base *makeReceiver() {
  static_assert(sizeof(Fixture) == sizeof(Base));
  static_assert(alignof(Fixture) == alignof(Base));
  auto *fixture = new Fixture;
  Base *base = fixture;
  require(static_cast<void *>(fixture) == static_cast<void *>(base));
  receiver = base;
  return base;
}
} // namespace

extern "C" void assignmentD0(Presonus::AssignmentHandler *) asm(
    "_ZN8Presonus17AssignmentHandlerD0Ev");
extern "C" void mixerD0(Presonus::MixerAssignmentHandler *) asm(
    "_ZN8Presonus22MixerAssignmentHandlerD0Ev");

extern "C" void realDelete(void *) asm("__real__ZdlPv");
extern "C" void wrappedDelete(void *) asm("__wrap__ZdlPv");
void wrappedDelete(void *pointer) {
  if (pointer == receiver) {
    realDelete(pointer);
    std::puts("delete");
    return;
  }
  realDelete(pointer);
}

int main(int argc, char **argv) {
  require(argc == 3 && std::strcmp(argv[2], "unbound") == 0);
  if (std::strcmp(argv[1], "AssignmentHandler") == 0)
    assignmentD0(makeReceiver<Presonus::AssignmentHandler, HandlerFixture>());
  else {
    require(std::strcmp(argv[1], "MixerAssignmentHandler") == 0);
    mixerD0(
        makeReceiver<Presonus::MixerAssignmentHandler, MixerHandlerFixture>());
  }
}
