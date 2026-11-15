#include "presonus/panel/SystemAboutPage.hpp"
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <sstream>
#include <string>
using namespace Core::Portable;
struct Observer final : ParamObserverBase {
  const char *name;
  std::string &trace;
  Observer(const char *n, std::string &t) : name(n), trace(t) {}
  void paramChanged(Parameter *p, int message) override {
    char text[100];
    std::snprintf(text, sizeof(text), "%s:%d:%.9g;", name, message,
                  static_cast<double>(p->getValue()));
    trace += text;
  }
};
int main(int argc, char **argv) {
  if (argc < 6)
    return 2;
  const bool independentProvider = std::strcmp(argv[1], "provider") == 0;
  const bool present = std::atoi(argv[2]);
  const float initial = std::strtof(argv[3], nullptr);
  const float defaultValue = std::strtof(argv[4], nullptr);
  const bool feedback = std::atoi(argv[5]);
  ParamInfo info =
      PARAM_FLOAT(10, "store", -2, 2, defaultValue, 0, nullptr, nullptr, 0, 0);
  NumericParam parameter(info);
  parameter.setValue(initial, false);
  std::string trace;
  Observer controller("C", trace), observer("O", trace);
  parameter.setController(&controller);
  parameter.addObserver(&observer);
  parameter.setFeedbackNeeded(feedback);
  if (independentProvider) {
    for (int i = 6; i < argc; ++i) {
      // Operations come from executed original instructions, not store().
      if (!present)
        return 3;
      float value;
      int edit;
      if (std::sscanf(argv[i], "set:%f:%d", &value, &edit) == 2)
        parameter.NumericParam::setValue(value, edit != 0);
      else if (std::sscanf(argv[i], "reset:%d", &edit) == 1)
        parameter.NumericParam::resetValue(edit != 0);
      else
        return 4;
    }
  } else {
    Presonus::Panel::SystemAboutPage page(present ? &parameter : nullptr);
    page.store();
  }
  std::printf("%.9g %s\n", static_cast<double>(parameter.getValue()),
              trace.c_str());
  parameter.removeObserver(&observer);
  parameter.setController(nullptr);
}
