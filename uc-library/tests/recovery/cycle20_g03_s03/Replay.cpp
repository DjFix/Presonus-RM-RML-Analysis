#include "presonus/surface/sl_mixer_encoder.hpp"

#include <cstdlib>
#include <iostream>

using namespace Core::Portable;

struct Observer final : Component {
  void paramChanged(Parameter *p, int message) override {
    std::cout << (message == Parameter::kEdit ? "edit" : "change") << ' '
              << p->getTag() << ' ' << p->getValue() << ' ';
  }
};

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  Observer observer;
  Presonus::Surface::EQPageComponent page;
  const ParamInfo info =
      PARAM_FLOAT(1000, "encoder_mode", 0, 4, 0, 1, 0, 0, 0, 0);
  auto &list = presonus::surface::PageObserverAccess::encoderParameters(page);
  list.add(info, true);
  auto *parameter = list.byTag(1000);
  parameter->setValue(std::atoi(argv[2]), false);
  parameter->setController(&observer);
  parameter->setFeedbackNeeded(true);
  page.onShow(std::atoi(argv[1]));
  parameter->setController(nullptr);
  std::cout << static_cast<int>(parameter->getValue()) << '\n';
}
