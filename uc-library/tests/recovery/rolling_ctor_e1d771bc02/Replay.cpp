#include "presonus/surface/CalibrateTouchComponent.hpp"
#include <iostream>
#include <string>

namespace {
using Page = Presonus::Surface::CalibrateTouchComponent;
using Core::Portable::Component;

unsigned destroyed = 0;
struct Child : Component {
  ~Child() override { ++destroyed; }
};

void printState(Presonus::PageComponent &page) {
  std::cout << page.getName().str() << '\n'
            << page.getFormName() << '\n'
            << page.getPageTag() << '\n';
}
} // namespace

int main(int argc, char **argv) {
  if (argc == 1) {
    {
      Page page(presonus::surface::CalibrateTouchInit{});
      printState(page);
      page.addChild(new Child);
    }
  } else if (argc == 3) {
    {
      Page page(argv[1], std::stoi(argv[2]));
      printState(page);
      page.addChild(new Child);
      page.addChildren(new Core::Portable::TComponentArray<Child>(2));
    }
  } else {
    return 2;
  }
  std::cout << destroyed << '\n';
}
