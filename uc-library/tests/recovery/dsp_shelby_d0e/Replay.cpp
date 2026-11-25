#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

#include <cstdlib>
#include <new>

namespace {
void *receiver = nullptr;
unsigned sequence = 0;
unsigned releaseOrder = 0;
unsigned deleteOrder = 0;

void deallocate(void *pointer) {
  if (pointer == receiver) {
    deleteOrder = ++sequence;
    receiver = nullptr;
  }
  std::free(pointer);
}

struct Target final : Core::IPropertyHandler {
  void setProperty(const Core::Property &) override {}
  void getProperty(Core::Property &) override {}
  void release() override { releaseOrder = ++sequence; }
};
} // namespace

void operator delete(void *pointer) noexcept { deallocate(pointer); }
void operator delete(void *pointer, std::size_t) noexcept {
  deallocate(pointer);
}

int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  unsigned expectedRelease, expectedDelete;
  if (!(fixture >> expectedRelease >> expectedDelete))
    return 2;
  Target target;
  auto *controller = new ShelbyGEQController(0x1337, 0x2468);
  receiver = controller;
  controller->setTarget(&target);
  controller->makeTargetOwner();
  controller->release();
  std::cout << "1 deleting destructor case\n";
  return releaseOrder != expectedRelease || deleteOrder != expectedDelete ||
         sequence != 2 || receiver;
}
