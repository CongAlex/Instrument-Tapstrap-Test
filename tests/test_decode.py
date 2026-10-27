import pytest

from tapstrap.decode import (FingerAccelSample, ImuSample, SensorConfig, decode_notification,
                             encode_for_test)


def test_finger_accel_scaling_4g():
    cfg = SensorConfig(finger_accel_g=4)
    raw = [128, 0, -128] * 5           # 128 LSB * 7.81 mg = 0.99968 g
    out = decode_notification(encode_for_test([("accl", 12345, raw)]), cfg)
    assert len(out) == 1 and isinstance(out[0], FingerAccelSample)
    s = out[0]
    assert s.device_ms == 12345
    assert s.index == pytest.approx((0.99968, 0.0, -0.99968))
    assert s.magnitudes()[0] == pytest.approx(0.99968 * 2 ** 0.5)


def test_imu_scaling_and_multiple_messages():
    cfg = SensorConfig(imu_gyro_dps=2000, imu_accel_g=16)
    data = encode_for_test([
        ("imu", 100, [1000, -1000, 0, 2048, 0, -2048]),
        ("accl", 101, list(range(15))),
        ("imu", 105, [0] * 6),
    ])
    out = decode_notification(data, cfg)
    assert [type(s) for s in out] == [ImuSample, FingerAccelSample, ImuSample]
    assert out[0].gyro_dps == pytest.approx((70.0, -70.0, 0.0))
    assert out[0].accel_g == pytest.approx((0.999424, 0.0, -0.999424))
    assert out[1].device_ms == 101


def test_zero_padding_and_truncation_stop_cleanly():
    cfg = SensorConfig()
    data = encode_for_test([("imu", 7, [1] * 6)]) + b"\x00" * 8
    assert len(decode_notification(data, cfg)) == 1
    truncated = encode_for_test([("accl", 9, [0] * 15)])[:-4]
    assert decode_notification(truncated, cfg) == []


def test_command_bytes_and_validation():
    assert SensorConfig(16, 125, 2).command_bytes == [4, 1, 1]
    with pytest.raises(ValueError):
        SensorConfig(finger_accel_g=3)
