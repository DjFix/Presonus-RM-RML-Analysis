#include "presonus/uc/NetworkItem.hpp"
#include <cstdint>
#include <iostream>
#include <string>

using Presonus::UC::NetworkItem;

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;
  const auto type = static_cast<NetworkItem::Type>(std::stoul(argv[1]));
  NetworkItem item(type);
  const auto &description = item.portableDescription();
  std::cout << static_cast<std::uint32_t>(item.portableType()) << '\n'
            << (item.getComponent() != nullptr) << '\n'
            << item.isAccessAcquired() << '\n'
            << description.identifier << '\n'
            << description.contextKind << '\n'
            << description.port << '\n'
            << description.flags << '\n';
  for (const auto *field :
       {&description.hostAddress, &description.hostName,
        &description.applicationName, &description.applicationVersion,
        &description.category, &description.cid, &description.pid})
    std::cout << field->str() << '\n';
}
