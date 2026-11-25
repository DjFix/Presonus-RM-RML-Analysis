#include "presonus/dsp/ControllerInfo.hpp"
#include "presonus/dsp/SLReverbController.hpp"
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 3)
    return 2;
  const Presonus::Dsp::SLReverbController reverb(3);
  const Presonus::Dsp::Controller &control = reverb;
  auto volatile getter = &Presonus::Dsp::Controller::getParameterInfo;
  Presonus::Dsp::ParamInfo info{0x3417,
                                nullptr,
                                nullptr,
                                0xf1f2,
                                0x7851,
                                0x137f,
                                static_cast<unsigned>(std::stoul(argv[2])),
                                nullptr};
  (control.*getter)(info, std::stoi(argv[1]));
  const auto text = [](const char *value) { return value ? value : "-"; };
  std::cout << info.tag << '\n'
            << text(info.text0) << '\n'
            << text(info.text1) << '\n'
            << info.flags << '\n'
            << info.word10 << '\n'
            << info.word14 << '\n'
            << info.byteSize << '\n'
            << text(info.text2) << '\n';
}
