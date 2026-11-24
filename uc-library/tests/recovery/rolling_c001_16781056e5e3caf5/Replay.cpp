#include "presonus/uc/ServerComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <iostream>
#include <string_view>
int main() {
  for (const char *name : {"one", "two", "three"}) {
    Presonus::UC::ServerComponent server(name);
    Presonus::UC::MessageAttributes attributes(name);
    attributes.setSource("test-source");
    server.notify(attributes);
    if (std::string_view(server.getName()) != name || server.countChildren() ||
        std::string_view(attributes.getID()) != name ||
        std::string_view(attributes.getSource()) != "test-source")
      return 1;
    std::cout << "unchanged\n";
  }
}
