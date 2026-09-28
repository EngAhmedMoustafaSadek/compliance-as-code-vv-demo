Feature: Pulse rate estimation
  The monitor estimates pulse rate from a pulsatile physiological signal.

  @REQ-002 @RC-04
  Scenario Outline: Rate is accurate across the physiological range
    Given a clean pulsatile signal at <bpm> bpm sampled at 100 Hz for 10 seconds
    When the pulse rate is estimated
    Then the estimate is within 2 bpm of <bpm>

    Examples:
      | bpm |
      | 40  |
      | 60  |
      | 100 |
      | 150 |
      | 180 |

  @REQ-003 @RC-05
  Scenario: Too little data is rejected
    Given a clean pulsatile signal at 70 bpm sampled at 100 Hz for 3 seconds
    When the pulse rate is estimated
    Then the estimate is rejected as insufficient data
