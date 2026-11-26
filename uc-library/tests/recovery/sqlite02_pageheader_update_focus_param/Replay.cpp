#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface/PageHeaderComponent.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

#include <cstdio>
#include <cstdlib>
#include <string_view>

namespace {
using namespace Core::Portable;

struct Parameters {
  ParamInfo stringInfo{};
  ParamInfo aliasInfo{};
  StringParam previous{stringInfo};
  StringParam selected{stringInfo};
  StringParam alternate{stringInfo};
  StringParam label{stringInfo};
  AliasParam input{aliasInfo};
  AliasParam focus{aliasInfo};

  Parameter *pick(std::string_view name) {
    if (name == "old")
      return &previous;
    if (name == "new")
      return &selected;
    if (name == "alternate")
      return &alternate;
    if (name == "-")
      return nullptr;
    std::abort();
  }

  const char *name(const Parameter *parameter) const {
    if (parameter == &previous)
      return "old";
    if (parameter == &selected)
      return "new";
    if (parameter == &alternate)
      return "alternate";
    if (!parameter)
      return "-";
    std::abort();
  }
};

class Handler final : public Presonus::MixerAssignmentHandler {
public:
  Handler(int index, std::string_view response, const char *label,
          Parameters &parameters)
      : index_(index), response_(response), label_(label),
        parameters_(parameters) {}

  void *castTo(int type) override {
    std::printf("cast %d %d\n", index_, type);
    return MixerAssignmentHandler::castTo(type);
  }
  const char *getName() const override { return "replay"; }
  void updateConnections() override {}
  void onMappingParamChanged(Parameter *) override {}
  bool getParamFocusInfo(FocusInfo &info, Parameter *parameter) override {
    std::printf("focus %d %s\n", index_, parameters_.name(parameter));
    if (index_ == 0 || response_ == "miss")
      return false;
    info.sourcePort.label = label_;
    if (response_ == "alternate")
      info.sourcePort.alternateOriginal = &parameters_.alternate;
    return true;
  }

private:
  int index_;
  std::string_view response_;
  const char *label_;
  Parameters &parameters_;
};

class Observer final : public ParamObserverBase {
public:
  explicit Observer(const Parameters &params) : parameters_(params) {}
  void paramChanged(Parameter *p, int message) override {
    if (message != Parameter::kChanged)
      std::abort();
    std::puts(p == &parameters_.focus ? "changed focus" : "changed label");
  }

private:
  const Parameters &parameters_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 8)
    return EXIT_FAILURE;
  Parameters params;
  params.focus.setOriginal(params.pick(argv[2]));
  params.label.fromString(argv[7], false);

  const std::string_view input = argv[1];
  Parameter *parameter = nullptr;
  if (input.starts_with("alias-")) {
    params.input.setOriginal(params.pick(input.substr(6)));
    parameter = &params.input;
  } else if (input == "unbound") {
    parameter = &params.input;
  } else if (input != "null") {
    parameter = params.pick(input);
  }

  Handler decline(0, argv[3], argv[4], params);
  Handler last(1, argv[3], argv[4], params);
  Core::Vector<Presonus::AssignmentHandler *> entries;
  entries.add(nullptr);
  entries.add(&decline);
  entries.add(&last);
  Presonus::AssignmentHandlerTable assignments(entries);
  Presonus::Surface::PageHeaderComponent page(
      "focus", argv[5][0] == '1' ? &params.focus : nullptr,
      argv[6][0] == '1' ? &params.label : nullptr, assignments);

  Observer observer(params);
  params.focus.addObserver(&observer);
  params.label.addObserver(&observer);
  page.updateFocusParam(parameter);
  params.focus.removeObserver(&observer);
  params.label.removeObserver(&observer);

  char label[128];
  params.label.toString(label, sizeof label);
  std::printf("result %s %s\n", params.name(params.focus.getOriginal()), label);
}
