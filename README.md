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

1. Open HACS in your Home Assistant instance.
2. Search for "Buienalarm" in the integrations section.
3. Click "Install" and restart Home Assistant.

## Configuration

### Configuration via UI

1. Go to **Settings** > **Devices & Services**.
2. Click **Add Integration**.
3. Search for **Buienalarm** and follow the configuration prompts.

### YAML Configuration (Optional)

Alternatively, you can configure the component using YAML:

```yaml
# Example configuration.yaml entry
buienalarm:
  latitude: 52.3676  # Optional, defaults to Home Assistant latitude
  longitude: 4.9041  # Optional, defaults to Home Assistant longitude
  monitored_conditions:
    - precipitation
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
