#include "core/portable/coreparams.h"
#include "presonus/SLChannel.hpp"
#include "presonus/surface/FatChannelClipboard.hpp"
#include <iostream>
#include <string>
int main(int argc, char **argv) {
  bool observe = argc == 2 && std::string(argv[1]) == "--observe-provider";
  Presonus::SLChannelBase channel("channel");
  Core::Portable::Component unrelated("unrelated");
  int cases[][4] = {{0, 0, 0, 218},          {1348563553, 0, 0, 218},
                    {1348563553, 1, 0, 218}, {1348563553, 1, 1, 218},
                    {1348563553, 1, 2, 218}, {1348563553, 1, 2, 217},
                    {1348563553, 1, 2, -1}};
  Presonus::Surface::FatChannelClipboard::CopyPasteFilter filter({});
  if (observe)
    std::cout << '[';
  int index = 0;
  for (auto &c : cases) {
    Core::Portable::ParamInfo info{};
    info.tag = c[3];
    Core::Portable::NumericParam parameter(info);
    if (c[2])
      parameter.setController(c[2] == 2 ? &channel : &unrelated);
    if (observe) {
      if (index++)
        std::cout << ',';
      std::cout << "{\"type\":" << c[0] << ",\"object\":" << c[1]
                << ",\"controller\":" << (parameter.getController() != nullptr)
                << ",\"channel\":"
                << (Core::Portable::core_cast<Presonus::SLChannelBase>(
                        parameter.getController()) != nullptr)
                << ",\"tag\":" << parameter.getTag() << '}';
    } else
      std::cout << filter.shouldSave(c[0], nullptr, c[1] ? &parameter : nullptr)
                << ' ';
  }
  if (observe)
    std::cout << ']';
  std::cout << '\n';
}
