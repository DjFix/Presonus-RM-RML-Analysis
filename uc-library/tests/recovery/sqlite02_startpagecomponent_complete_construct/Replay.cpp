#include "presonus/surface/StartPageComponent.hpp"
#include <cstdlib>
#include <iostream>

using namespace Core::Portable;
using StartPage = Presonus::Surface::StartPageComponent;

struct DerivedPage : StartPage {
  DerivedPage(const char *name, const char *form, int tag)
      : StartPage(name, form, tag) {}
  DerivedPage() = default;

  bool feedback() const { return paramList.isFeedbackNeeded(); }
  void addMode(Parameter *parameter) { paramList.add(parameter); }
};

template <typename Page> bool inspect(Page &page) {
  std::cout << page.getName() << '\n'
            << page.getFormName() << '\n'
            << page.getPageTag() << '\n';
  for (int index = 0; index < 2; ++index) {
    auto *parameter = page.getParameterAt(index);
    if (!parameter || !AliasParam::cast(parameter) ||
        parameter->getOriginal() ||
        page.getParameterByTag(parameter->getTag()) != parameter)
      return false;
    std::cout << parameter->getType() << ' ' << parameter->getTag() << ' '
              << parameter->getName() << ' ' << parameter->isOwnInfo() << ' '
              << parameter->isPublic() << ' ' << parameter->isStorable() << ' '
              << parameter->isLinkable() << ' ' << parameter->isMutable() << ' '
              << parameter->isReadOnly() << ' ' << parameter->isUserFlag1()
              << ' ' << parameter->isUserFlag2() << ' ' << parameter->getValue()
              << '\n';
  }
  std::cout << page.isDawMode() << ' ' << page.isMidiMode() << '\n';
  return true;
}

int main(int argc, char **argv) {
  const ParamInfo daw = PARAM_TOGGLE(1000, "suppliedDaw", 1, nullptr, 0);
  const ParamInfo midi = PARAM_TOGGLE(1001, "suppliedMidi", 0, nullptr, 0);
  if (argc == 1) {
    DerivedPage page;
    auto *dawParameter = new NumericParam(daw);
    auto *midiParameter = new NumericParam(midi);
    page.addMode(dawParameter);
    page.addMode(midiParameter);
    return page.getParameterByTag(1000) == dawParameter &&
                   page.getParameterByTag(1001) == midiParameter &&
                   page.isDawMode() && !page.isMidiMode()
               ? 0
               : 1;
  }
  if (argc != 4)
    return 2;
  const int tag = std::atoi(argv[3]);
#ifdef START_PAGE_BASE_CONSTRUCTOR
  DerivedPage page(argv[1], argv[2], tag);
  if (!page.feedback())
    return 3;
#else
  StartPage page(argv[1], argv[2], tag);
#endif
  if (!inspect(page))
    return 4;
  NumericParam dawValue(daw);
  NumericParam midiValue(midi);
  auto *dawAlias = AliasParam::cast(page.getParameterByTag(1000));
  auto *midiAlias = AliasParam::cast(page.getParameterByTag(1001));
  dawAlias->setOriginal(&dawValue);
  midiAlias->setOriginal(&midiValue);
  std::cout << page.isDawMode() << ' ' << page.isMidiMode() << '\n';
  dawAlias->setOriginal(&midiValue);
  midiAlias->setOriginal(&dawValue);
  std::cout << page.isDawMode() << ' ' << page.isMidiMode() << '\n';
  dawAlias->setOriginal(nullptr);
  midiAlias->setOriginal(nullptr);
}
