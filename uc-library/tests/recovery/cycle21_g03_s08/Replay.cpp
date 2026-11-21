#include "presonus/surface/sl_mixer_encoder.hpp"
#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using namespace Presonus::Surface;
using presonus::surface::PageObserverAccess;

struct Observer final : EQPageComponent::IObserver {
  explicit Observer(int id) : id(id) {}
  void onEqEncoderModeChanged() override { std::cout << id << '\n'; }
  int id;
};

int main(int argc, char **argv) {
  if (argc < 3)
    return 2;
  EQPageComponent page;
  Observer first(0), second(1);
  for (int index = 3; index < argc; ++index)
    page.addObserver(std::atoi(argv[index]) == 0 ? &first : &second);
  ParamInfo info = PARAM_TOGGLE(std::atoi(argv[1]), "encoder", 0, 0, 0);
  auto &parameters = PageObserverAccess::encoderParameters(page);
  auto *parameter = parameters.add(info);
  page.paramChanged(parameter, std::atoi(argv[2]));
}
