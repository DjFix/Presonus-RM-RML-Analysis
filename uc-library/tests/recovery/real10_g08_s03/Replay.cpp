#include "core/system/coretime.h"
#include "presonus/panel/AlertBook.hpp"
#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <ctime>
using namespace Core::Portable;
static std::int64_t nanoTime;
extern "C" int __wrap_clock_gettime(clockid_t id, timespec *t) {
  if (id != CLOCK_MONOTONIC)
    std::abort();
  t->tv_sec = nanoTime / 1000000000;
  t->tv_nsec = nanoTime % 1000000000;
  return 0;
}
struct InspectParam final : NumericParam {
  using NumericParam::NumericParam;
  int observers() const { return observerList.count(); }
  int counts[4]{};
  int sets = 0;
  void setValue(float v, bool edit) override {
    if (sets == 4)
      std::abort();
    counts[sets++] = observers();
    NumericParam::setValue(v, edit);
  }
};
static void hex(const char *p) {
  for (; *p; ++p)
    std::printf("%02x", static_cast<unsigned char>(*p));
}
int main(int argc, char **argv) {
  if (argc != 7)
    return 2;
  bool deactivate = !std::strcmp(argv[1], "deactivate");
  bool selection = std::atoi(argv[2]);
  int duplicate = std::atoi(argv[3]);
  int shape = std::atoi(argv[4]);
  nanoTime = std::strtoll(argv[5], nullptr, 10);
  int mode = std::atoi(argv[6]);
  const ParamInfo infos[] = {PARAM_STRING(100, "first", 0),
                             PARAM_STRING(101, "second", 0),
                             PARAM_STRING(102, "third", 0)};
  const ParamInfo wrong[] = {
      PARAM_FLOAT(101, "wrong", 0, 1, 0, 1, "", nullptr, 0, 0)};
  const ParamInfo numeric =
      PARAM_FLOAT(9, "selected", 0, 1, 0, 1, "", nullptr, 0, 0);
  Component provider("alert");
  if (shape != 1)
    provider.addParameters(infos, 1);
  if (shape == 2)
    provider.addParameters(wrong, 1);
  else if (shape != 1)
    provider.addParameters(infos + 1, 1);
  provider.addParameters(infos + 2, 1);
  InspectParam parameter(numeric);
  for (int i = 0; i < duplicate; ++i)
    parameter.addObserver(&provider);
  Presonus::Panel::AlertBook book(provider);
  auto *page = reinterpret_cast<Presonus::Panel::Page *>(&mode);
  book.setup(page, selection ? &parameter : nullptr, "alpha", "", "omega",
             mode);
  if (deactivate)
    book.deactivated();
  const auto &s = book.portableAlertState();
  std::printf("{\"mode\":%d,\"page_preserved\":%s,\"selection_present\":%s,"
              "\"milliseconds\":%lld,\"parameter_value\":%d,\"observers\":%d,"
              "\"text\":[",
              s.mode, s.page == page ? "true" : "false",
              s.selection ? "true" : "false",
              static_cast<long long>(s.startedMilliseconds),
              parameter.getValue() == 1.f ? 1 : 0, parameter.observers());
  for (int tag = 100; tag <= 102; ++tag) {
    if (tag != 100)
      std::putchar(',');
    auto *p = provider.getParameterByTag(tag);
    auto *str = p ? StringParam::cast(p) : nullptr;
    if (!str)
      std::printf("null");
    else {
      std::putchar('"');
      hex(str->getText());
      std::putchar('"');
    }
  }
  std::printf("],\"set_observer_counts\":[");
  for (int i = 0; i < parameter.sets; ++i)
    std::printf("%s%d", i ? "," : "", parameter.counts[i]);
  std::printf("]}\n");
  // All test registrations released before provider/parameter lifetime ends.
  while (parameter.observers())
    parameter.removeObserver(&provider);
}
