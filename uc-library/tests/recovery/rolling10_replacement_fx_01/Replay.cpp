#include "presonus/mixer/GambitRMLApplication.hpp"
#include <array>
#include <cstring>
#include <iomanip>
#include <iostream>
#include <stdexcept>
int main() {
  unsigned input;
  const Presonus::Mixer::GambitRMLApplication object(
      Presonus::Mixer::GambitRMLApplication::SourcePortConstruction{});
  while (std::cin >> input) {
    char s0[] = "old0", s1[] = "old1", s2[] = "old2", s3[] = "old3";
    Presonus::UC::ServerInfo info;
    info.originalDescriptorSize = 0x10203000u + input;
    info.flags = 0xa5a5a500u + input;
    info.strings = {s0, s1, s2, s3};
    const auto before = info;
    unsigned short port = static_cast<unsigned short>(input);
    object.getNetworkSetup(port, info);
    if (info.originalDescriptorSize != before.originalDescriptorSize ||
        info.flags != before.flags || info.strings[1] != s1 ||
        info.strings[3] != s3 || std::strcmp(s0, "old0") ||
        std::strcmp(s1, "old1") || std::strcmp(s2, "old2") ||
        std::strcmp(s3, "old3"))
      throw std::runtime_error("unexpected write or ownership mutation");
    std::cout << port << ' ' << std::quoted(info.strings[0]) << ' '
              << std::quoted(info.strings[2]) << '\n';
  }
}
