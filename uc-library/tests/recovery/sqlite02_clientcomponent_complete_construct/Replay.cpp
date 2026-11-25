#include "presonus/uc/ClientComponent.hpp"
#include "presonus/uc/message_attributes.hpp"
#include <cstring>

using Core::Portable::Component;
using Presonus::UC::ClientComponent;
using Presonus::UC::MessageAttributes;

namespace {
class Child : public Component {
public:
  explicit Child(bool &destroyed)
      : Component("owned-child"), destroyed_(destroyed) {}
  ~Child() override { destroyed_ = true; }

private:
  bool &destroyed_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 2 && argc != 3)
    return 1;
  const char *name = argc == 3 ? argv[2] : nullptr;
  bool destroyed = false;
  {
    ClientComponent object(name);
    Component &base = object;
    if (std::strcmp(base.getName(), name ? name : "") != 0 ||
        base.getParent() != nullptr || base.countChildren() != 0 ||
        base.countParameters() != 0 || base.getParameterAt(0) != nullptr)
      return 2;
    const MessageAttributes message("fixture");
    object.notify(message);
    if (base.countChildren() != 0 || base.countParameters() != 0)
      return 3;
    base.addChild(new Child(destroyed));
    if (base.countChildren() != 1 || base.getChild(0)->getParent() != &base)
      return 4;
  }
  return destroyed ? 0 : 5;
}
