#include "presonus/panel/AlertBook.hpp"

#include <array>
#include <cstdint>
#include <cstdlib>
#include <ctime>
#include <iostream>
#include <string>
#include <tuple>
#include <type_traits>

using namespace Core::Portable;
using Presonus::Panel::AlertBook;
using Presonus::Panel::Page;

namespace {
std::int64_t nanoTime;
unsigned clockReads;

struct Selection final : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
  void setValue(float value, bool edit) override {
    ++sets;
    NumericParam::setValue(value, edit);
  }
  unsigned sets = 0;
};

struct Observer final : Component {
  Observer() : Component("replay observer") {}
  void paramChanged(Parameter *, int) override { ++events; }
  unsigned events = 0;
};

auto observe(AlertBook &book, Component &provider, const Selection &selection,
             const Observer &listener) {
  const auto state = book.portableAlertState();
  std::array<std::string, 3> values;
  for (unsigned index = 0; index < values.size(); ++index) {
    auto *parameter = provider.getParameterByTag(100 + static_cast<int>(index));
    if (auto *text = parameter ? StringParam::cast(parameter) : nullptr)
      values[index] = text->getText();
    else
      values[index] = parameter
                          ? "numeric:" + std::to_string(parameter->getValue())
                          : "absent";
  }
  return std::make_tuple(state.mode, state.page, state.selection,
                         state.startedMilliseconds, selection.getValue(),
                         selection.observers(), selection.sets, values,
                         listener.events, clockReads);
}
} // namespace

extern "C" int __wrap_clock_gettime(clockid_t id, timespec *time) {
  if (id != CLOCK_MONOTONIC)
    std::abort();
  ++clockReads;
  time->tv_sec = nanoTime / 1000000000;
  time->tv_nsec = nanoTime % 1000000000;
  return 0;
}

int main() {
  static_assert(
      std::is_same_v<decltype(&AlertBook::previous), void (AlertBook::*)()>);
  const ParamInfo first[] = {PARAM_STRING(100, "first", 0)};
  const ParamInfo second[] = {PARAM_STRING(101, "second", 0)};
  const ParamInfo third[] = {PARAM_STRING(102, "third", 0)};
  const ParamInfo wrong[] = {
      PARAM_FLOAT(101, "wrong", 0, 1, 0, 1, "", nullptr, 0, 0)};
  const ParamInfo selected =
      PARAM_FLOAT(9, "selected", 0, 1, 0, 1, "", nullptr, 0, 0);
  int mode, pagePresent, selectionPresent, duplicate, shape;
  while (std::cin >> mode >> pagePresent >> selectionPresent >> duplicate >>
         nanoTime >> shape) {
    Component provider("alert");
    if (shape != 1)
      provider.addParameters(first, 1);
    if (shape == 2)
      provider.addParameters(wrong, 1);
    else if (shape != 1)
      provider.addParameters(second, 1);
    provider.addParameters(third, 1);
    Observer listener;
    for (int tag = 100; tag <= 102; ++tag)
      if (auto *parameter = provider.getParameterByTag(tag))
        parameter->addObserver(&listener);

    Selection selection(selected);
    if (duplicate)
      selection.addObserver(&provider);
    AlertBook book(provider);
    auto *page = pagePresent ? reinterpret_cast<Page *>(&mode) : nullptr;
    book.setup(page, selectionPresent ? &selection : nullptr, "first text", "",
               "third text", mode);
    const auto before = observe(book, provider, selection, listener);
    if (std::get<0>(before) != mode || std::get<1>(before) != page ||
        std::get<2>(before) != (selectionPresent ? &selection : nullptr) ||
        std::get<3>(before) != nanoTime / 1000000 ||
        std::get<4>(before) != (selectionPresent ? 1.f : 0.f))
      return 2;
    book.previous();
    const bool unchanged =
        before == observe(book, provider, selection, listener);
    while (selection.observers())
      selection.removeObserver(&provider);
    for (int tag = 100; tag <= 102; ++tag)
      if (auto *parameter = provider.getParameterByTag(tag))
        parameter->removeObserver(&listener);
    std::cout << unchanged << '\n';
  }
  return std::cin.eof() ? 0 : 3;
}
