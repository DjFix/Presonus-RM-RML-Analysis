#include "presonus/panel/RoguePanelRegistrar.hpp"

#include <cstring>
#include <iostream>
#include <type_traits>

using Presonus::Panel::RoguePanelRegistrar;
static_assert(std::is_same_v<decltype(&RoguePanelRegistrar::getLcdPortName),
                             const char *(RoguePanelRegistrar::*)()>);

int main(int argc, char **argv) {
  if (argc != 2)
    return 1;

  const char *saved = nullptr;
  for (int index = 0; index < 3; ++index) {
    RoguePanelRegistrar receiver{};
    int countBefore = -1;
    const int *tagsBefore = receiver.getTags(20, countBefore);
    const int group = index + 1;
    const int groupSize = receiver.getParamInfoListSizeFromGroup(group);
    const char *name = receiver.getLcdPortName();
    if (name == nullptr || std::strcmp(name, argv[1]) != 0 ||
        receiver.getLcdPortName() != name ||
        (saved != nullptr && saved != name))
      return 2;
    saved = name;
    int countAfter = -1;
    const int *tagsAfter = receiver.getTags(20, countAfter);
    if (tagsBefore != tagsAfter || countBefore != countAfter ||
        groupSize != receiver.getParamInfoListSizeFromGroup(group))
      return 3;
    std::cout << "case " << index << '\n';
  }
  return std::strcmp(saved, argv[1]) == 0 ? 0 : 4;
}
