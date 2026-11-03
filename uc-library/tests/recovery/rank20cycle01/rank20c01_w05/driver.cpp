#include "presonus/rank20cycle01/rank20c01_w05.hpp"
#include <cstring>
#include <iostream>
#include <string>
using Core::Portable::Component;
static int deleted = 0;
class Child : public Component {
public:
  ~Child() override { ++deleted; }
};
int main() {
  for (const char *name : {"", "scene", "filter_group",
                           "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789ABCDEFGHIJKLMNO"
                           "PQRSTUVWXYZ0123456789"}) {
    Component provider(name);
    Presonus::Mixer::FilterGroupManager actual(name);
    if (std::strcmp(provider.getName(), actual.getName()) ||
        actual.getParent() ||
        actual.countChildren() != provider.countChildren() ||
        actual.countParameters() != provider.countParameters())
      return 1;
  }
  for (int count : {0, 1, 3}) {
    deleted = 0;
    {
      Component provider("provider");
      for (int i = 0; i < count; ++i)
        provider.addChild(new Child);
    }
    int expected = deleted;
    deleted = 0;
    {
      Presonus::Mixer::FilterGroupManager actual("actual");
      for (int i = 0; i < count; ++i)
        actual.addChild(new Child);
    }
    if (deleted != expected || deleted != count)
      return 2;
  }
  std::cout << "7 provider/source-port cases passed; names, defaults, actual "
               "owned-child cleanup\n";
}
