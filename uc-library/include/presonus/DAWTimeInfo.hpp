#pragma once

#include <array>
#include <cstdint>

namespace Core::Portable {
class Parameter;
}

namespace Presonus {
class DAWClientComponent;
namespace UC {
class MessageAttributes;
class TimeCodeEvent;
} // namespace UC

// Portable borrowed-state adapter. This declaration does not establish the
// original class layout or original, unencoded return type. The caller supplies
// at least 309 readable bytes representing the observed ARM object state.
class DAWTimeInfo {
public:
  explicit DAWTimeInfo(const std::uint8_t *borrowedState) noexcept
      : borrowedState_(borrowedState) {}

  // Independent borrowed 24-byte record adapters. Counts and storage must
  // describe readable records; these are not original ARM class layouts.
  class TimeSignatureMap {
  public:
    TimeSignatureMap(const std::uint8_t *records, int count) noexcept
        : records_(records), count_(count) {}
    // Pointer-valued native behavior; original return declaration unresolved.
    const std::uint8_t *findItem(double) const;

  private:
    const std::uint8_t *records_;
    int count_;
  };
  class TempoMap {
  public:
    TempoMap(const std::uint8_t *records, int count) noexcept
        : records_(records), count_(count) {}
    const std::uint8_t *findItem(double) const;

  private:
    const std::uint8_t *records_;
    int count_;
  };

  // unsigned int preserves the full zero-extended ARM r0 observation; the
  // original source return declaration remains unresolved.
  unsigned int isMusicalDisplay() const;

  // Independent mutable source-port state; no original layout/ownership claim.
  struct TimeString {
    std::array<char, 32> clockText{};
    std::array<std::int32_t, 4> clockValues{};
    std::array<char, 32> musicalText{};
    std::array<std::int32_t, 4> musicalValues{};
  };
  // Independent application boundary; required services never default to
  // no-ops.
  struct Services {
    struct Item {
      unsigned format;
      std::array<std::int32_t, 4> values;
    };
    virtual ~Services() = default;
    virtual void updateTempo(const UC::MessageAttributes &) = 0;
    virtual void updateSignature(const UC::MessageAttributes &) = 0;
    virtual std::array<Core::Portable::Parameter *, 3>
    parameters(DAWClientComponent &) = 0;
    virtual unsigned eventKind(const UC::TimeCodeEvent &) const = 0;
    virtual unsigned count(const UC::TimeCodeEvent &) const = 0;
    virtual Item item(const UC::TimeCodeEvent &, unsigned) const = 0;
    virtual void append(UC::TimeCodeEvent &, const Item &) = 0;
    virtual void print(std::array<char, 32> &, const Item &,
                       unsigned digits) = 0;
    virtual void locate(DAWClientComponent &, const TimeString &, bool musical,
                        bool blocked) = 0;
    virtual void locateRelative(DAWClientComponent &, int, const TimeString &,
                                bool musical, bool blocked) = 0;
  };
  struct State {
    Services *services = nullptr;
    DAWClientComponent *client = nullptr;
    bool musicalDisplay = false;
    bool milliSeconds = false;
    bool locating = false;
    std::array<Core::Portable::Parameter *, 3> parameters{};
    std::array<TimeString, 3> times{};
  };
  DAWTimeInfo(const std::uint8_t *borrowedState, State &mutableState) noexcept
      : borrowedState_(borrowedState), sourceState_(&mutableState) {}
  void updateTimeContext(const UC::MessageAttributes &);
  void init(DAWClientComponent *);
  void locateTransport(const TimeString &);
  void locateTransportRelative(int);
  void updateTime(const UC::TimeCodeEvent &);
  void parseTime(const UC::TimeCodeEvent &, TimeString &) const;
  void createTimeEvent(UC::TimeCodeEvent &, const TimeString &);
  void setMusicalDisplay(bool);
  void displayMilliSeconds(bool);
  void updateTimeParam(Core::Portable::Parameter *, const TimeString &);

private:
  Services &services() const;
  State &mutableState();
  const std::uint8_t *borrowedState_;
  State *sourceState_ = nullptr;
};

} // namespace Presonus
