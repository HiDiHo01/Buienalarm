[![Dependabot Updates](https://github.com/HiDiHo01/Buienalarm/actions/workflows/dependabot/dependabot-updates/badge.svg?branch=main)](https://github.com/HiDiHo01/Buienalarm/actions/workflows/dependabot/dependabot-updates)
# Buienalarm Home Assistant Component

This is a custom component for Home Assistant that integrates with Buienalarm to provide accurate and up-to-date precipitation forecasts.

## Features

- Real-time precipitation forecasts for your location.
- Supports custom locations by latitude and longitude.
- Fully configurable through the Home Assistant UI.

## Installation

### Manual Installation

1. Download the latest version of this repository from [GitHub](https://github.com/HiDiHo01/Buienalarm).
2. Extract the `buienalarm` folder into your Home Assistant `custom_components` directory:
   ```
   <config>/custom_components/buienalarm/
   ```
3. Restart Home Assistant.

### HACS Installation
[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=HiDiHo01&repository=Buienalarm&category=integration)

or
1. Open HACS in your Home Assistant instance.
2. Click on the hamburger menu (three dots)
3. Click custom repositories (Aangepaste repositories)
4. Add https://github.com/HiDiHo01/Buienalarm/
5. Type integration
6. Click "Add" and restart Home Assistant.
7. Follow steps Configuration via UI

## Configuration

### Configuration via UI

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration**.
3. Search for **Buienalarm** and follow the configuration prompts.

### Example apexcharts-card

<img src="https://github.com/HiDiHo01/Buienalarm/blob/main/images/buienalarm%20card.png">

```
type: custom:apexcharts-card
graph_span: 2h
show:
  last_updated: true
span:
  start: minute
  offset: "-10m"
now:
  show: true
  label: Nu
  color: white
header:
  show: true
  title: Neerslag in mm/u (+2 uur)
series:
  - entity: sensor.neerslag_verwacht
    name: Neerslag
    unit: mm/u
    stroke_width: 8
    show:
      extremas: true
      header_color_threshold: true
    float_precision: 1
    type: line
    opacity: 1
    color: "#44739e"
    color_threshold:
      - value: 0
        color: "#89CFF0"
        opacity: 0.3
      - value: 0.1
        color: "#89CFF0"
        opacity: 0.4
      - value: 0.2
        color: "#87CEEB"
        opacity: 0.8
      - value: 0.4
        color: "#4473ff"
      - value: 0.6
        color: "#000080"
      - value: 0.8
        color: "#000080"
      - value: 1
        color: darkblue
      - value: 2
        color: "#000044"
    data_generator: |
      return entity.attributes.precipitation_data.map((record, index) => {
        return [record.time, record.precipitationrate, record.precipitationtype];
      });
experimental:
  color_threshold: true
apex_config:
  tooltip:
    x:
      format: HH:mm
  xaxis:
    type: datetime
    labels:
      useSeriesColors: true
      datetimeFormatter:
        hour: HH:mm
      format: HH:mm
  chart:
    height: 300px
    animations:
      enabled: true
      easing: easeinout
      speed: 2000
      animateGradually:
        enabled: true
        delay: 500
```

## Entities Provided

This integration creates the following sensor entities:

- `sensor.duur_neerslag`
- `sensor.neerslag`
- `sensor.buienalarm`
- `sensor.my_buienalarm`
- `sensor.neerslag_komend_uur`
- `sensor.neerslag_verwacht`
- `sensor.neerslag_omschrijving`
- `sensor.soort_neerslag`

## Customization

You can customize how the data is displayed in the Home Assistant UI by using Lovelace cards.

## Troubleshooting

If you encounter issues, check the Home Assistant logs for error messages related to the Buienalarm component. You can enable debug logging for detailed information:

```yaml
logger:
  default: warning
  logs:
    custom_components.buienalarm: debug
```

## Contributing

Contributions are welcome! If you find bugs or have feature requests, please open an issue or submit a pull request on [GitHub](https://github.com/HiDiHo01/Buienalarm).

## License

This project is licensed under the MIT License. See the [LICENSE](https://github.com/HiDiHo01/Buienalarm/blob/main/LICENSE) file for details.
