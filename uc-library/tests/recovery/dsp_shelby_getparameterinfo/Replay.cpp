#include "presonus/mixer_dsp/Dsp.hpp"
#include <bit>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <string>

using Presonus::Dsp::ShelbyGEQController;

#include "presonus/dsp/ControllerInfo.hpp"
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  std::ifstream fixture(argv[1]);
  int index, tag;
  unsigned requested, size, flags, word10, word14;
  std::string name, label, unit;
  unsigned count = 0;
  while (fixture >> index >> requested >> size >> tag >> flags >> word10 >>
         word14 >> std::quoted(name) >> std::quoted(label) >>
         std::quoted(unit)) {
    ShelbyGEQController controller;
    Presonus::Dsp::ParamInfo info;
    info.flags = requested;
    info.byteSize = size;
    info.text2 = "sentinel";
    controller.getParameterInfo(info, index);
    if (info.tag != tag || info.flags != flags || info.word10 != word10 ||
        info.word14 != word14 || info.byteSize != size || !info.text0 ||
        name != info.text0 || !info.text1 || label != info.text1 ||
        !info.text2 || unit != info.text2) {
      std::cerr << "index " << index << " observed " << info.tag << ' '
                << info.flags << ' ' << info.word10 << ' ' << info.word14 << ' '
                << std::quoted(info.text0) << ' ' << std::quoted(info.text1)
                << ' ' << std::quoted(info.text2) << '\n';
      return 1;
    }
    ++count;
  }
  std::cout << count << " getParameterInfo cases\n";
  return count != 4;
}
