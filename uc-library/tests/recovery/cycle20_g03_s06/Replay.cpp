#include "presonus/surface/ChannelInfoPageComponent.hpp"

#include <cstdlib>
#include <iomanip>
#include <iostream>

using namespace Core::Portable;
using Page = Presonus::Surface::ChannelInfoPageComponent;

namespace {
class Observer : public Component {
public:
  void paramChanged(Parameter *parameter, int message) override {
    if (message != Parameter::kChanged && message != Parameter::kEdit)
      return;
    char value[256]{};
    parameter->toString(value, sizeof value);
    std::cout << (message == Parameter::kEdit ? "edit" : "change") << ' '
              << parameter->getTag() << ' ' << std::quoted(value) << '\n';
  }
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 11)
    return 2;
  const int task = std::atoi(argv[1]);
  Page page;
  page.bindIconSkinDirectory(FileName(argv[2]));
  const auto type = static_cast<Page::ListType>(std::atoi(argv[3]));
  const int delta = std::atoi(argv[4]);
  auto &state = page.sourcePortIconLists();
  state = {std::atoi(argv[5]), std::atoi(argv[6]), std::atoi(argv[7]),
           std::atoi(argv[8])};
  if (task == 6) {
    std::cout << "result " << page.getMaxListOffset(type) << ' '
              << page.getMaxListOffset(type) << '\n';
    return 0;
  }

  Observer observer;
  const ParamInfo icon = PARAM_STRING(300, "ch_icon", 0);
  page.addParameters(&icon, 1, true);
  page.findParameter("ch_icon")->fromString(argv[9], false);
  const int missingTag = std::atoi(argv[10]);
  for (int firstTag : {100, 200}) {
    for (int row = 0; row < 5; ++row) {
      const int tag = firstTag + 2 * row;
      const ParamInfo label = PARAM_STRING(tag, "label", 0);
      const ParamInfo value =
          PARAM_FLOAT(tag + 1, "value", 0, 1, 0.5f, 0.01f, 0, 0, 0, 0);
      for (const auto *info : {&label, &value}) {
        if (info->tag == missingTag)
          continue;
        page.addParameters(info, 1, true);
        auto *param = page.getParameterByTag(info->tag);
        if (info == &label)
          param->fromString("old", false);
        param->setController(&observer);
        param->setFeedbackNeeded(true);
      }
    }
  }

  if (task == 7)
    page.updateList(type);
  else if (task == 8)
    page.addListOffset(type, delta);
  else if (task == 9)
    page.categoryChanged();
  else
    return 2;

  std::cout << "state " << state.categoryOffset << ' ' << state.iconOffset
            << ' ' << state.selectedCategory << ' ' << state.selectedIcon
            << '\n';
  for (int i = 0; i < page.countParameters(); ++i)
    page.getParameterAt(i)->setController(nullptr);
}
