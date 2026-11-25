#include "presonus/uc/NetworkItem.hpp"
#include <cstring>
#include <iomanip>
#include <iostream>
#include <string>

int main(int argc, char **argv) {
  if (argc != 6)
    return 1;
  using Presonus::UC::NetworkItem;
  NetworkItem item(static_cast<NetworkItem::Type>(std::stoul(argv[1])));
  auto &description = item.portableDescription();
  description.applicationName = argv[2];
  description.applicationVersion = argv[3];
  description.hostAddress = argv[4];
  description.hostName = argv[5];
  Core::CStringBuffer<128> title;
  std::memset(title.getBuffer(), 0xa5, title.getSize() - 1);
  title.getBuffer()[title.getSize() - 1] = 0;
  static_cast<const NetworkItem &>(item).getTitle(title);
  for (int index = 0; index < title.getSize(); ++index)
    std::cout << std::setfill('0') << std::setw(2) << std::hex
              << static_cast<unsigned>(
                     static_cast<unsigned char>(title.str()[index]));
  std::cout << '\n';
}
