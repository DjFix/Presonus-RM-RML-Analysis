#include "presonus/MeterControl.hpp"
#include "presonus/rank20cycle01/rank20c01_w02.hpp"
#include <iostream>
#include <string_view>

namespace {
class Child : public Core::Portable::Component {
public:
  explicit Child(int &count) : count_(count) {}
  ~Child() override { ++count_; }

private:
  int &count_;
};
template <class Parent> int observe(int children) {
  int destroyed = 0;
  {
    Parent parent;
    for (int i = 0; i < children; ++i)
      parent.addChild(new Child(destroyed));
  }
  return destroyed;
}
} // namespace
int main(int argc, char **argv) {
  if (argc != 2)
    return 2;
  if (std::string_view(argv[1]) == "meter") {
    int left, top, right, bottom;
    while (std::cin >> left >> top >> right >> bottom) {
      Presonus::MeterControl meter(Core::Rect(left, top, right, bottom));
      std::cout << static_cast<int>(meter.isHorizontal()) << '\n';
    }
    return 0;
  }
  bool provider = std::string_view(argv[1]) == "provider";
  if (!provider && std::string_view(argv[1]) != "port")
    return 2;
  for (int children : {0, 1, 2, 7}) {
    int destroyed = provider ? observe<Core::Portable::Component>(children)
                             : observe<Presonus::MackieControlUnit>(children);
    std::cout << children << ' ' << destroyed << '\n';
  }
}
