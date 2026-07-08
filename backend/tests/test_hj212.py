from app.services.hj212 import HJ212Message, build_data_ack, parse_message


REALTIME_SAMPLE = "##0247QN=20260706103512345;ST=21;CN=2011;PW=123456;MN=A110000_0001;Flag=9;CP=&&DataTime=20260706103000;w01010-Rtd=28.6,w01010-Flag=N;w01014-Rtd=7.8,w01014-Flag=N;w01001-Rtd=6.5,w01001-Flag=N;w01017-Rtd=15.2,w01017-Flag=N;w01019-Rtd=1.023,w01019-Flag=N&&1540\r\n"

HOURLY_SAMPLE = "##0247QN=20260706103512345;ST=21;CN=2061;PW=123456;MN=A110000_0001;Flag=9;CP=&&DataTime=20260706100000;w01010-Avg=28.4,w01010-Flag=N;w01014-Avg=7.7,w01014-Flag=N;w01001-Avg=6.6,w01001-Flag=N;w01017-Avg=15.0,w01017-Flag=N;w01019-Avg=1.022,w01019-Flag=N&&5280\r\n"


def test_parse_realtime_hj212_message() -> None:
    message = parse_message(REALTIME_SAMPLE)

    assert isinstance(message, HJ212Message)
    assert message.cn == "2011"
    assert message.mn == "A110000_0001"
    assert message.data_time.strftime("%Y%m%d%H%M%S") == "20260706103000"
    assert message.metrics[0].code == "w01010"
    assert message.metrics[0].value_key == "Rtd"
    assert message.metrics[0].value == 28.6
    assert message.metrics[0].flag == "N"


def test_parse_hourly_hj212_message() -> None:
    message = parse_message(HOURLY_SAMPLE)

    assert message.cn == "2061"
    assert message.metrics[0].value_key == "Avg"
    assert message.metrics[-1].code == "w01019"
    assert message.metrics[-1].value == 1.022


def test_build_data_ack_reuses_message_metadata() -> None:
    message = parse_message(REALTIME_SAMPLE)

    ack = build_data_ack(message)

    assert ack.startswith("##")
    assert "ST=91" in ack
    assert "CN=9014" in ack
    assert "MN=A110000_0001" in ack
    assert "QN=20260706103512345" in ack
    assert "CP=&&&&" in ack
