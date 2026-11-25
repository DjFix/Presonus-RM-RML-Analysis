#include "presonus/surface/AssignmentHandlerTable.hpp"
#include "presonus/surface_panel/ControlHelpers.hpp"

#include <cstdio>
#include <cstdlib>
#include <memory>
#include <vector>

namespace {
class Handler final : public Presonus::MixerAssignmentHandler {
public:
  Handler(int index, char behavior, bool parameterExpected)
      : index_(index), behavior_(behavior),
        parameterExpected_(parameterExpected) {}

  void *castTo(int tag) override {
    std::printf("cast %d %d\n", index_, tag);
    return behavior_ == 'n' ? nullptr : MixerAssignmentHandler::castTo(tag);
  }
  const char *getName() const override { return ""; }
  void updateConnections() override {}
  void onMappingParamChanged(Core::Portable::Parameter *) override {}
  bool getParamFocusInfo(FocusInfo &info,
                         Core::Portable::Parameter *parameter) override {
    if (parameterExpected_ != (parameter != nullptr))
      std::abort();
    std::printf("focus %d %d\n", index_, parameter != nullptr);
    char marker[16];
    std::snprintf(marker, sizeof marker, "%d", index_ + 1);
    info.sourcePort.label = marker;
    return behavior_ == 't';
  }

private:
  int index_;
  char behavior_;
  bool parameterExpected_;
};
} // namespace

int main(int argc, char **argv) {
  if (argc != 4)
    return EXIT_FAILURE;
  const bool hasParameter = std::atoi(argv[2]) != 0;
  const bool borrowedMode = std::atoi(argv[3]) != 0;
  Core::Portable::ParamInfo parameterInfo{};
  Core::Portable::StringParam parameter(parameterInfo);
  Core::Vector<Presonus::AssignmentHandler *> entries;
  Presonus::AssignmentHandlerTable borrowed(entries);
  Presonus::AssignmentHandlerTable owned;
  std::vector<std::unique_ptr<Handler>> handlers;
  for (int index = 0; argv[1][index]; ++index) {
    Handler *handler = nullptr;
    if (argv[1][index] != '-') {
      handlers.push_back(
          std::make_unique<Handler>(index, argv[1][index], hasParameter));
      handler = handlers.back().get();
    }
    if (borrowedMode)
      entries.add(handler);
    else
      owned.addHandler(handler);
  }
  Presonus::MixerAssignmentHandler::FocusInfo info;
  info.sourcePort.label = "0";
  auto &table = borrowedMode ? borrowed : owned;
  const bool result =
      table.getParamFocusInfo(info, hasParameter ? &parameter : nullptr);
  std::printf("result %d %s\n", result, info.sourcePort.label.str());
}
