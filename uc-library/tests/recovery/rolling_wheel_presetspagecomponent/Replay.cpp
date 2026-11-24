#include "core/portable/gui/coreview.h"

#define main replayPreviousPresetsCases
#include "../../graph_trial06_presets_tests.cpp"
#undef main

int main(int argc, char **argv) {
  if (argc != 8)
    return 2;
  Config config{};
  config.mixer = config.handler = 1;
  config.count = std::stoi(argv[1]);
  config.rows = std::stoi(argv[2]);
  config.offset = std::stoi(argv[3]);
  config.selected = std::stoi(argv[4]);
  config.visible = std::stoi(argv[5]);
  const WheelEvent event(std::stoi(argv[6]),
                         static_cast<WheelEvent::Axis>(std::stoi(argv[7])));
  Capture capture;
  Parameters params;
  for (int row = 0; row < config.rows; ++row) {
    params.text(row * 3, capture);
    params.value(row * 3 + 1, capture);
  }
  PresetsPageState state{0,    config.rows, config.offset, config.selected,
                         true, params};
  Boundary boundary(config, capture);
  {
    Presonus::Surface::PresetsPageComponent page(state, boundary);
    page.onWheelInput(event);
    if (event.delta != std::stoi(argv[6]) || event.axis != std::stoi(argv[7]))
      return 3;
  }
  std::cout << "{\"offset\":" << state.offset
            << ",\"selected\":" << state.selected << ",\"events\":[";
  const char *separator = "";
  for (const auto &entry : capture.events) {
    std::cout << separator << std::quoted(entry);
    separator = ",";
  }
  std::cout << "]}\n";
}
