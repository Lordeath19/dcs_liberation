import {
  useOpenNewTgoPackageDialogMutation,
  useOpenTgoInfoDialogMutation,
} from "../../api/liberationApi";
import { Tgo as TgoModel } from "../../api/liberationApi";
import SplitLines from "../splitlines/SplitLines";
import { Icon, Point } from "leaflet";
import { Symbol as MilSymbol } from "milsymbol";
import { Marker, Tooltip } from "react-leaflet";

function iconForTgo(cp: TgoModel) {
  const symbol = new MilSymbol(cp.sidc, {
    size: 24,
  });

  return new Icon({
    iconUrl: symbol.toDataURL(),
    iconAnchor: new Point(symbol.getAnchor().x, symbol.getAnchor().y),
  });
}

interface TgoProps {
  tgo: TgoModel;
}

export default function Tgo(props: TgoProps) {
  const [openNewPackageDialog] = useOpenNewTgoPackageDialogMutation();
  const [openInfoDialog] = useOpenTgoInfoDialogMutation();

  const isScouted = Boolean(props.tgo.scouted);

  return (
    <Marker
      position={props.tgo.position}
      icon={iconForTgo(props.tgo)}
      eventHandlers={{
        click: () => {
          if (isScouted) {
            openInfoDialog({tgoId: props.tgo.id});
          }
        },
        contextmenu: () => {
          if (isScouted) {
            openNewPackageDialog({tgoId: props.tgo.id});
          }
        },
      }}
    >
      <Tooltip>
        <>
          {`${props.tgo.name} (${props.tgo.control_point_name})`}
          <br />
          {isScouted ? (
            <SplitLines items={props.tgo.units} />
          ) : (
            <>Unscouted | recon required</>
          )}
        </>
      </Tooltip>
    </Marker>
  );
}
